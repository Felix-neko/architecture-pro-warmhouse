from typing import Optional, Dict, Any, Union, Iterable
import os
from datetime import timedelta, datetime, timezone
import asyncio
import logging
import struct
from uuid import uuid4


import aiokafka

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.structs import ConsumerRecord


from telemetry_dto import (
    TELEMETRY_STATUS_EVENTS_TOPIC,
    TelemetrySample,
    SensorStatusEvent,
    TelemetrySampleFormat,
    FloatTelemetrySample,
    CustomTelemetrySample,
    MeasurementStartedStatusEvent,
    MeasurementStoppedStatusEvent,
    StatusEventTypeAdapter,
)


def deserialize_sample(record: aiokafka.ConsumerRecord, sample_format: TelemetrySampleFormat) -> TelemetrySample:
    if sample_format == TelemetrySampleFormat.FLOAT:
        timestamp_seconds = record.timestamp / 1000.0
        ts_from_record = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        blob = record.value
        if blob is None:
            return FloatTelemetrySample(timestamp=ts_from_record, value=None)
        else:
            (has_val,) = struct.unpack(">?", blob[:1])
            if has_val is None:
                return FloatTelemetrySample(timestamp=ts_from_record, value=None)
            else:
                (val,) = struct.unpack(">f", blob[1:5])
                return FloatTelemetrySample(timestamp=ts_from_record, value=val)
    else:
        raise NotImplementedError("Other formats aren't implemented yet!")


def serialize_sample(sample: TelemetrySample, sample_format: TelemetrySampleFormat) -> bytes:
    if sample_format == TelemetrySampleFormat.FLOAT:
        if sample.value is None:
            # flag=False, no float data follows
            return struct.pack(">?", False)
        else:
            # flag=True followed by the float value
            return struct.pack(">?f", True, sample.value)
    else:
        raise NotImplementedError("Other formats aren't implemented!")


class TelemetryQueueProcessor:
    _STATUS_EVENTS_TOPIC_RETENTION_DAYS = 5

    def __init__(self, kafka_url: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self._is_initialized = False
        self._kafka_url = kafka_url if kafka_url is not None else os.getenv("KAFKA_URL", "localhost:9092")
        self._kafka_admin: Optional[AIOKafkaAdminClient] = None

    async def initialize(self):
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
            self.logger.info("Closing Kafka admin client")
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
    _SAMPLES_CONSUMER_GRPOUP_ID = "samples_default_cgid"

    def __init__(self, kafka_url: Optional[str] = None):
        self._status_event_consumer: Optional[AIOKafkaConsumer] = None
        self._sample_consumer: Optional[AIOKafkaConsumer] = None
        self._sample_topic_subscriptions = {}  # topic_name --> TelemetryFormat
        self._listen_samples_task = None

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
        self._sample_consumer = AIOKafkaConsumer(
            bootstrap_servers=self._kafka_url,
            group_id=self._SAMPLES_CONSUMER_GRPOUP_ID,
            enable_auto_commit=True,
        )
        await self._status_event_consumer.start()
        await self._sample_consumer.start()

    async def listen_samples(self):
        self.logger.info("Listening samples")
        print(self._sample_consumer.subscription())
        if not self._is_initialized:
            await self.initialize()

        try:
            async for message in self._sample_consumer:
                try:
                    # Get the sample format for this topic
                    sample_format = self._sample_topic_subscriptions[message.topic]

                    # Deserialize the sample
                    sample = deserialize_sample(message, sample_format)
                    self.logger.info(f"Sample from {message.topic}: {sample}")

                    # Process the sample
                    self.process_sample(message.topic, sample)

                except Exception as e:
                    self.logger.error(f"Error processing sample from {message.topic}: {e}")
        except asyncio.CancelledError:
            self.logger.info("Sample listener task cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in sample listener: {e}")
            raise

    def process_sample(self, topic: str, sample: TelemetrySample):
        print(topic, sample)

    async def listen_status_events(self):
        if not self._is_initialized:
            await self.initialize()

        async for message in self._status_event_consumer:
            self.logger.info(f"Received message in status queue: {message.value}")
            try:
                status_event = StatusEventTypeAdapter.validate_json(message.value)
                if isinstance(status_event, MeasurementStartedStatusEvent):
                    # Create a consumer for this status_event.kafka_topic_name
                    # place it to consumer
                    self._sample_topic_subscriptions[status_event.kafka_topic_name] = status_event.sampling_format
                    self._sample_consumer.unsubscribe()
                    self._sample_consumer.subscribe(list(self._sample_topic_subscriptions.keys()))
                    if self._listen_samples_task is not None:
                        self._listen_samples_task.cancel()
                    self._listen_samples_task = asyncio.create_task(self.listen_samples())
            except Exception as ex:
                self.logger.error(ex)


class TelemetryPublisher(TelemetryQueueProcessor):
    def __init__(
        self,
        sensor_name: str,
        topic_uuid_str: str,
        sample_format: TelemetrySampleFormat,
        kafka_url: Optional[str] = None,
    ):
        super().__init__(kafka_url=kafka_url)

        self.sensor_name = sensor_name
        self.topic_uuid_str = topic_uuid_str
        self.topic_name = f"telemetry_samples__{sensor_name}__{sample_format.value}__{topic_uuid_str}"
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
            serialized = serialize_sample(samples, self.sample_format)
            await self.kafka_producer.send_and_wait(self.topic_name, serialized)
        else:
            # Multiple samples - send in parallel and gather results
            futures = []
            for s in samples:
                serialized = serialize_sample(s, self.sample_format)
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

    sensor_uuid = uuid4()
    sensor_name = "float_temp_sensor_1"

    publisher = TelemetryPublisher(sensor_name, str(sensor_uuid), TelemetrySampleFormat.FLOAT)
    await publisher.initialize()

    await publisher._create_topic(publisher.topic_name)

    # starting measurement
    measurement_start_event = MeasurementStartedStatusEvent(
        timestamp=datetime.now().astimezone(),
        sensor_uuid=sensor_uuid,
        sensor_name=sensor_name,
        kafka_topic_name=publisher.topic_name,
        sampling_format=publisher.sample_format,
        sampling_interval=0.2,
    )

    await publisher.push_status_event(measurement_start_event)

    # Create and push some float telemetry samples.

    # Create some sample temperature readings
    samples = [
        FloatTelemetrySample(value=22.5 + i * 0.5)  # Temperature increasing by 0.5°C each sample
        for i in range(5)  # Create 5 samples
    ]

    # Push the samples
    logging.info(f"Pushing {len(samples)} float samples to {publisher.topic_name}")
    await publisher.push_samples(samples)
    logging.info(f"Pushed {len(samples)} float samples to {publisher.topic_name}")

    # end measurement
    measurement_stop_event = MeasurementStoppedStatusEvent(
        timestamp=datetime.now().astimezone(),
        kafka_topic_name=publisher.topic_name,
        sensor_uuid=sensor_uuid,
        sensor_name=sensor_name,
    )
    await publisher.push_status_event(measurement_stop_event)

    # Clean up
    await publisher.close()


async def push_and_listen():
    # Create the subscriber
    subscriber = TelemetrySubscriber()
    await subscriber.initialize()

    # Start listening in the background
    event_listener_task = asyncio.create_task(subscriber.listen_status_events())
    # sample_listener_task = asyncio.create_task(subscriber.listen_samples())

    try:
        # Push some events
        await push_some_events()

        # Keep running to continue listening
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        event_listener_task.cancel()
        # sample_listener_task.cancel()
        try:
            await event_listener_task
            # await sample_listener_task
        except asyncio.CancelledError:
            pass
        await subscriber.close()


if __name__ == "__main__":
    try:
        asyncio.run(push_and_listen())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    print("^__^")
