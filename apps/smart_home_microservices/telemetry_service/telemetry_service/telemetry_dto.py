"""
pydantic-классы и enum'ы для передачи телеметрических данных
"""

from datetime import datetime
from typing import Optional, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


########################################################################
# Измерения телеметрии (сыплется часто, в основном простые данные)
########################################################################


class TelemetrySampleType(str, Enum):
    CUSTOM = "CUSTOM"  # Данные произвольного JSON-формата
    FLOAT_WITH_TIMESTAMP = "FLOAT_WITH_TIMESTAMP"  # timestamp + бинарная float-чиселка
    FLOAT = "FLOAT"  # Только бинарные float-данные, timestamp проставляется средствами KAFKA
    INT = "INT"  # Только бинарные int-данные, timestamp проставляется средствами kafka
    BOOL = "BOOL"  # Только бинарные bool-данные, timestamp проставляется средствами kafka
    TEXT = "TEXT"  # Только текстовые данные в UTF-8


class TelemetrySample(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now().astimezone())


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


class SensorStatusEvent(StatusEvent):
    sensor_id: int = Field(description="Уникальное ID датчика, уникально в рамках нашего умного дома")
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
    sample_format: TelemetrySampleType = Field(description="")
    frequency: Optional[float] = Field(
        description="Частота сбора данных, с которой сервис работы с датчиком датчик будет закидывать данные в очередь"
    )


class MeasurementStoppedStatusEvent(SensorStatusEvent):
    """
    Датчик закончил измерение, удалите kafka-топик, когда закончите его сгружать в БД
    """

    sensor_id: int
    kafka_topic_name: str = Field(description="Kafka-топик, от которого надо будет отписаться, когда прочитаем данные")


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
