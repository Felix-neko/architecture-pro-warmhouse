"""
pydantic-классы и enum'ы для передачи телеметрических данных
"""

from datetime import datetime
from typing import Optional, Any, Annotated, Union
from typing_extensions import Literal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, TypeAdapter
from typing_extensions import Literal


TELEMETRY_STATUS_EVENTS_TOPIC = "telemetry_status_events"


########################################################################
# Измерения телеметрии (сыплется часто, в основном простые данные)
########################################################################


class TelemetrySampleFormat(str, Enum):
    """
    В каком формате заливать телеметрию в очередь.
    NB: FLOAT_WITH_TIMESTAMP и FLOAT потом будует конвертироваться в один и тот же класс FloatTelemetrySample)
    """

    CUSTOM = "CUSTOM"  # Данные произвольного JSON-формата
    FLOAT_WITH_TIMESTAMP = "FLOAT_WITH_TIMESTAMP"  # timestamp + бинарная float-чиселка
    FLOAT_BINARY = "FLOAT_BINARY"  # Только бинарные float-данные, timestamp проставляется средствами KAFKA
    INT = "INT"  # Только бинарные int-данные, timestamp проставляется средствами kafka
    BOOL = "BOOL"  # Только бинарные bool-данные, timestamp проставляется средствами kafka
    TEXT = "TEXT"  # Только текстовые данные в UTF-8


class TelemetrySample(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    value: Optional[Any] = None


class FloatTelemetrySample(TelemetrySample):
    value: Optional[float] = None


class IntTelemetrySample(TelemetrySample):
    value: Optional[int] = None


class BoolTelemetrySample(TelemetrySample):
    value: Optional[bool] = None


class TextTelemetrySample(TelemetrySample):
    value: Optional[str] = None


class CustomTelemetrySample(TelemetrySample):
    value: Optional[Any] = None  # Any JSON‑serializable type or null


###############################################################
# Служебные события датчиков (реже, но разнообразнее)
###############################################################


class StatusEvent(BaseModel):
    timestamp: datetime

    def __init_subclass__(cls, **kwargs):
        """
        Нужно, чтобы работал TypeAdapter с дискриминатором
        """
        super().__init_subclass__(**kwargs)
        # Automatically add the literal discriminator field
        cls.__annotations__["event_class_name"] = Literal[cls.__name__]
        # Set the default value
        setattr(cls, "event_class_name", cls.__name__)


class SensorStatusEvent(StatusEvent):
    sensor_uuid: UUID = Field(description="UUID датчика, уникально в рамках нашего умного дома")
    sensor_name: Optional[str] = Field(default=None, description="Мнемоническое имя для отображения датчика")


class SensorCreatedStatusEvent(SensorStatusEvent):
    pass


class SensorDeletedStatusEvent(SensorStatusEvent):
    pass


class SensorInfoStatusEvent(SensorStatusEvent):
    message: str


class SensorWarningStatusEvent(SensorInfoStatusEvent):
    pass


class SensorErrorStatusEvent(SensorWarningStatusEvent):
    pass


class SensorOtherStatusEvent(SensorStatusEvent):
    model_config = ConfigDict(from_attributes=True, extra="allow")


class MeasurementStartedStatusEvent(SensorStatusEvent):
    """
    Датчик начал измерение: нужно подписаться на такой-то kafka-топик, чтобы их сгрузить в БД.
    """

    kafka_topic_name: str = Field(description="Kafka-топик, на который надо подписаться, чтобы читать данные")
    sampling_format: TelemetrySampleFormat = Field(description="")
    sampling_interval: Optional[float] = Field(description="Интервал сбора данных (секунды)")


class MeasurementStoppedStatusEvent(SensorStatusEvent):
    """
    Датчик закончил измерение, удалите kafka-топик, когда закончите его сгружать в БД
    """

    sensor_uuid: UUID
    kafka_topic_name: str = Field(description="Kafka-топик, от которого надо будет отписаться, когда прочитаем данные")


# Discriminated union with only concrete subclasses
StatusEventUnion = Annotated[
    Union[
        SensorCreatedStatusEvent,
        SensorDeletedStatusEvent,
        SensorInfoStatusEvent,
        SensorWarningStatusEvent,
        SensorErrorStatusEvent,
        SensorOtherStatusEvent,
        MeasurementStartedStatusEvent,
        MeasurementStoppedStatusEvent,
    ],
    Field(discriminator="event_class_name"),
]

# Create TypeAdapter for the discriminated union
StatusEventTypeAdapter = TypeAdapter(StatusEventUnion)


class SensorStatusEventType(str, Enum):
    SENSOR_CREATED = "SENSOR_CREATED"
    SENSOR_DELETED = "SENSOR_DELETED"
    SENSOR_INFO = "SENSOR_INFO"
    SENSOR_WARNING = "SENSOR_WARNING"
    SENSOR_ERROR = "SENSOR_ERROR"
    SENSOR_OTHER = "SENSOR_OTHER"
    MEASUREMENT_STARTED = "MEASUREMENT_STARTED"
    MEASUREMENT_STOPPED = "MEASUREMENT_STOPPED"


sensor_event_classes = {
    SensorStatusEventType.SENSOR_CREATED: SensorCreatedStatusEvent,
    SensorStatusEventType.SENSOR_DELETED: SensorDeletedStatusEvent,
    SensorStatusEventType.SENSOR_INFO: SensorInfoStatusEvent,
    SensorStatusEventType.SENSOR_WARNING: SensorWarningStatusEvent,
    SensorStatusEventType.SENSOR_ERROR: SensorErrorStatusEvent,
    SensorStatusEventType.MEASUREMENT_STARTED: MeasurementStartedStatusEvent,
    SensorStatusEventType.MEASUREMENT_STOPPED: MeasurementStoppedStatusEvent,
}


if __name__ == "__main__":
    from datetime import datetime, timezone
    from uuid import uuid4

    # Create a UUID for the sensor
    sensor_uuid = uuid4()

    # Create instances of each event type
    events = [
        MeasurementStartedStatusEvent(
            timestamp=datetime.now(timezone.utc).astimezone(),
            sensor_uuid=sensor_uuid,
            sensor_name="Living Room Temperature",
            kafka_topic_name="temp_measurements_topic",
            sampling_format=TelemetrySampleFormat.FLOAT_BINARY,
            sampling_interval=0.1,
        ),
        MeasurementStoppedStatusEvent(
            timestamp=datetime.now(timezone.utc).astimezone(),
            sensor_uuid=sensor_uuid,
            sensor_name="Living Room Temperature",
            kafka_topic_name="temp_measurements_topic",
        ),
    ]

    for event in events:
        # Serialize to JSON bytes
        json_bytes = event.model_dump_json().encode("utf-8")
        # Deserialize back to object
        deserialized_event = StatusEventTypeAdapter.validate_json(json_bytes)
        print(f"\nEvent Type: {type(event)}")
        print(f"Original: {event}")
        print(f"Serialized: {json_bytes}")
        print(f"Deserialized: {deserialized_event}")
        print(f"Deserialized type: {type(deserialized_event)}")
        print(f"Correct type preserved: {type(event) == type(deserialized_event)}")
