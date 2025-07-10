from typing import Optional, Dict, Any, Union, Iterable
import os
from datetime import timedelta, datetime
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic


from telemetry_dto import (
    TELEMETRY_STATUS_EVENTS_TOPIC,
    TelemetrySample,
    SensorStatusEvent,
    TelemetrySampleFormat,
    FloatTelemetrySample,
    CustomTelemetrySample,
    MeasurementStartedStatusEvent,
)


class TelemetryQueueProcessor:
    _STATUS_EVENTS_TOPIC_RETENTION_DAYS = 5

    def __init__(self, kafka_url: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self._is_initialized = False
        self._kafka_url = kafka_url if kafka_url is not None else os.getenv("KAFKA_URL", "localhost:9092")
        self._kafka_admin: Optional[AIOKafkaAdminClient] = None

    async def initialize(
        self,
    ):
        """Initialize the Kafka connection and create status event topic."""

        self.logger.info(f"Initializing  with Kafka at {self._kafka_url}")

        self._kafka_admin = AIOKafkaAdminClient(bootstrap_servers=self._kafka_url)
        await self._kafka_admin.start()

        # Create status event topic (if not exists)
        await self._create_topic(
            TELEMETRY_STATUS_EVENTS_TOPIC, self._STATUS_EVENTS_TOPIC_RETENTION_DAYS, crash_if_exists=False
        )
        self.logger.info("TelemetryQueueProcessor initialized successfully")
        self._is_initialized = True

    async def _create_topic(self, topic_name: str, retention_days: int = 1, crash_if_exists: bool = True):
        # Check and create topic if needed
        topics = await self._kafka_admin.list_topics()
        if topic_name in topics:
            self.logger.info(f"Topic '{topic_name}' already exists")
            if crash_if_exists:
                raise ValueError(f"Topic '{topic_name}' already exists, crash_if_exists==True")
        else:
            self.logger.info(f"Creating topic: {topic_name}")
            retention_ms = str(int(timedelta(days=retention_days).total_seconds() * 1000))
            topic = NewTopic(
                name=topic_name,
                num_partitions=1,
                replication_factor=1,
                topic_configs={"retention.ms": retention_ms, "cleanup.policy": "delete"},
            )
            await self._kafka_admin.create_topics([topic])

    async def close(self):
        """Close Kafka connections."""
        if self._kafka_admin:
            self.logger.debug("Closing Kafka admin client")
            await self._kafka_admin.close()
            self.logger.info("Kafka admin client closed")

    def __del__(self):
        # Ensure resources are cleaned up
        async def cleanup():
            if hasattr(self, "_kafka_admin") and self._kafka_admin:
                await self._kafka_admin.close()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(cleanup())
            else:
                asyncio.run(cleanup())
        except Exception:
            # If we can't get the event loop, just ignore
            pass


class TelemetrySubscriber(TelemetryQueueProcessor):
    _STATUS_EVENTS_CONSUMER_GROUP_ID = "status_events_default_cgid"

    def __init__(self, kafka_url: Optional[str] = None):
        self._status_event_consumer: Optional[AIOKafkaConsumer] = None
        # self._consumer_group_id = consumer_group_id
        super().__init__(kafka_url=kafka_url)

    async def initialize(self):
        await super().initialize()
        # Create status event consumer
        self._status_event_consumer = AIOKafkaConsumer(
            TELEMETRY_STATUS_EVENTS_TOPIC,
            bootstrap_servers=self._kafka_url,
            group_id=self._STATUS_EVENTS_CONSUMER_GROUP_ID,
            enable_auto_commit=True,
        )
        await self._status_event_consumer.start()

    async def listen_status_events(self):
        if not self._is_initialized:
            await self.initialize()

        async for message in self._status_event_consumer:
            status_event = message.value

            self.logger.info(f"Received status event: {status_event}")


class TelemetryPublisher(TelemetryQueueProcessor):
    def __init__(
        self,
        sensor_name: str,
        topic_uuid: str,
        sample_format: TelemetrySampleFormat,
        kafka_url: Optional[str] = None,
    ):
        super().__init__(kafka_url=kafka_url)

        self.sensor_name = sensor_name
        self.topic_uuid = topic_uuid
        self.topic_name = f"{sensor_name}__{topic_uuid}__{sample_format.value}"
        self.sample_format = sample_format
        self.supported_sample_classes = ()
        self.kafka_producer: Optional[AIOKafkaProducer] = None

        def push_samples_sync(
            self,
            samples: Union[TelemetrySample, Iterable[TelemetrySample]],
            loop: Optional[asyncio.AbstractEventLoop] = None,
        ):
            if loop is None:
                asyncio.run(self.push_samples(samples))
            else:
                loop.run_until_complete(self.push_samples(samples))

        self.push_sample_sync = push_samples_sync

    async def initialize(self):
        await super().initialize()
        self.kafka_producer = AIOKafkaProducer(bootstrap_servers=self._kafka_url)
        await self.kafka_producer.start()

    async def push_status_event(self, status_event: SensorStatusEvent):
        await self.kafka_producer.send_and_wait(
            TELEMETRY_STATUS_EVENTS_TOPIC, status_event.model_dump_json().encode("utf-8")
        )

    def serialize_sample(self, sample: TelemetrySample) -> bytes:
        raise NotImplementedError("Implement it in child classes!")

    async def push_samples(self, samples: Union[TelemetrySample, Iterable[TelemetrySample]]):
        """
        Push one or more samples to Kafka.

        Args:
            samples: Either a single TelemetrySample or an iterable of TelemetrySamples

        Note:
            - For a single sample, uses send_and_wait for immediate confirmation
            - For multiple samples, sends them in parallel and waits for all to complete
        """
        if isinstance(samples, TelemetrySample):
            # Single sample - use send_and_wait for immediate confirmation
            serialized = self.serialize_sample(samples)
            await self.kafka_producer.send_and_wait(self.topic_name, serialized)
        else:
            # Multiple samples - send in parallel and gather results
            futures = []
            for s in samples:
                serialized = self.serialize_sample(s)
                future = self.kafka_producer.send(self.topic_name, serialized)
                futures.append(future)

            # Wait for all sends to complete
            if futures:
                await asyncio.gather(*futures)

    async def pop_sample(self) -> TelemetrySample:
        raise NotImplementedError("Implement it in child classes!")


# async def create_and_init_tqs() -> TelemetryQueueSubscriber:
#     tqs = TelemetryQueueSubscriber()
#     await tqs.initialize()
#     return tqs


async def listen_status_events():
    tqs = TelemetrySubscriber()
    await tqs.initialize()
    await tqs.listen_status_events()


async def push_some_events():
    tqp = TelemetryPublisher("sensor1", "uuid1", TelemetrySampleFormat.CUSTOM)
    await tqp.initialize()

    from uuid import uuid4

    event = MeasurementStartedStatusEvent(
        timestamp=datetime.now().astimezone(),
        sensor_uuid=uuid4(),
        sensor_name="Living Room Temperature",
        kafka_topic_name="temp_measurements_topic",
        sampling_format=TelemetrySampleFormat.FLOAT,
        sampling_interval=0.1,
    )

    await tqp.push_status_event(event)


if __name__ == "__main__":
    # tqs = asyncio.run(create_and_init_tqs())
    # asyncio.run(listen_status_events())
    asyncio.run(push_some_events())
    print("^__^")
