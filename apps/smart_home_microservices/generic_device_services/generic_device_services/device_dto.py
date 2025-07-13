"""
DTO-классы для устройств
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import Union, Optional, List, Any

from enum import Enum

from pydantic import BaseModel, Field, ConfigDict

from telemetry_dto import TelemetrySampleFormat


class DeviceType(str, Enum):
    SENSOR = "SENSOR"
    ACTUATOR = "ACTUATOR"
    OTHER = "OTHER"


class DeviceInfo(BaseModel):
    """Информация об устройстве"""

    device_id: int = Field(
        description="ID устройства в рамках своего сервиса (разные сервисы устройств будут смотреть на разные схемы БД)"
    )
    device_uuid: UUID = Field(
        default_factory=uuid4,
        description="Идентификатор устройства, глобально уникальный для каждого конкретного устройства, "
        "даже разных производителей и сервисов",
    )
    name: str = Field(description="Короткое и удобное имя устройства")
    display_name: Optional[str] = Field(
        default=None, description="Более подробное название, для отображения в интерфейсе"
    )
    model_name: Optional[str] = Field(default=None, description="Модель устройства (например, DS18B20)")
    device_type: DeviceType = Field(default=DeviceType.OTHER, description="Тип устройства")

    url: Optional[str] = Field(default=None, description="URL для доступа к устройства, если применимо")
    min_health_check_interval: Optional[bool] = Field(
        default=None, description="Минимальный интервал между проверками работоспособности устройства"
    )

    last_health_check: Optional[datetime] = Field(
        default=None, description="Время последней успешной проверки работоспособности"
    )

    is_active: Optional[bool] = Field(
        default=False, description="Включен/выключен (если его можно переводить в спящий режим без отключения от сети)"
    )

    is_alive: bool = Field(
        default=False,
        description="Доступно ли устройство по сети (если умеет это показывать отдельно от запроса на измерения)",
    )


class SensorType(str, Enum):
    """
    Тип датчика
    """

    TEMPERATURE = "TEMPERATURE"
    POWER_CONSUMPTION = "POWER_CONSUMPTION"
    CO2 = "CO2"
    SMOKE = "SMOKE"
    LEAK = "LEAK"
    FLUID_FLOW = "FLUID_FLOW"
    OTHER = "OTHER"


class SensorInfo(DeviceInfo):
    """Информация о датчике в системе."""

    sensor_type: SensorType = Field(default=SensorType.OTHER, description="Тип датчика (температура, CO2 и т.д.)")
    needs_polling: Optional[bool] = Field(
        default=None, description="Требуется ли опрашивать датчик (true) или он сам отправляет данные (false)"
    )

    min_sampling_interval: Optional[float] = Field(
        default=None, description="Минимальный интервал между опросами датчика в секундах"
    )


class MeasurementProcessInfo(BaseModel):
    """
    Информация о процессе измерения, запущенном на датчике.
    На одном датчике может быть запущено несколько процессов измерения одновременно.
    """

    sensor_id: int = Field(description="Идентификатор датчика, к которому относится процесс измерения")
    sample_format: TelemetrySampleFormat = Field(description="Формат данных, в котором датчик возвращает измерения")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now().astimezone(), description="Время запуска процесса измерения"
    )
    stopped_at: Optional[datetime] = Field(
        default=None, description="Время остановки процесса измерения (None, если процесс ещё выполняется)"
    )
    sampling_interval: Optional[float] = Field(
        default=None,
        description="Интервал между измерениями в секундах. Может быть None, если датчик сам посылает данные по необходимости",
    )


class DeviceSettingsInfo(BaseModel):
    """
    Настройки устройства.

    Объект с произвольными полями, схема определяется конкретным устройством и загружается отдельно.
    """

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "description": "Словарь с настройками датчика. Структура зависит от конкретной модели датчика."
        },
    )


class DeviceSettingsDataType(str, Enum):
    """Типы данных для отдельных настроек устройства"""

    INT = "INT"
    FLOAT = "FLOAT"
    BOOL = "BOOL"
    TEXT = "TEXT"
    JSON = "JSON"


class DeviceSettingsFieldInfo(BaseModel):
    """
    Метаданные: поля настроек.

    Содержит информацию, необходимую для генерации виджета настройки для настройки параметров устройства.
    """

    name: str = Field(description="Идентификатор поля в настройках")
    display_name: Optional[str] = Field(
        default=None, description="Человекочитаемое название поля для отображения в интерфейсе"
    )
    description: Optional[str] = Field(default=None, description="Подробное описание назначения и использования поля")
    data_type: DeviceSettingsDataType = Field(default=DeviceSettingsDataType.JSON, description="Тип данных поля")
    min_value: Optional[float] = Field(default=None, description="Минимальное допустимое значение (для числовых типов)")
    max_value: Optional[float] = Field(
        default=None, description="Максимальное допустимое значение (для числовых типов)"
    )
    allowed_values: Optional[List[Any]] = Field(
        default=None, description="Список допустимых значений (если поле может принимать только определённые значения)"
    )
