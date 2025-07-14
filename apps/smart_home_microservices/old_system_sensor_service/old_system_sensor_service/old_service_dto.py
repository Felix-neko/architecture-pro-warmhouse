# pydantic-классы для обмена данными со старым монолитом

from enum import Enum
from datetime import datetime


from pydantic import BaseModel, Field


class OldServiceTempSensorResponse(BaseModel):
    value: float = Field(description="Measured temperature value.")
    unit: str = Field(description="Unit of measurement (e.g., Celsius).")
    timestamp: datetime = Field(description="Timestamp when the measurement was taken.")
    location: str = Field(description="Location where the temperature was measured.")
    status: str = Field(description="Sensor status (e.g., active, inactive).")
    sensor_id: str = Field(description="Unique identifier of the sensor.")
    sensor_type: str = Field(description="Type of the sensor (e.g., temp, pressure, CO2, etc.")
    description: str = Field(description="Additional information about the sensor.")


class OldServiceTempSensorInfo(BaseModel):
    """
    Информация, получаемся от старого сервиса-монолита по конкретном датчику температуры или по списку таковых
    """

    id: int = Field(description="Unique identifier of the sensor")
    name: str = Field(description="Name of the sensor")
    type: str = Field(description="Type of the sensor")
    location: str = Field(description="Physical location of the sensor")
    value: float = Field(description="Current sensor reading")
    unit: str = Field(description="Unit of measurement for the sensor value")
    status: str = Field(description="Current status of the sensor")
    last_updated: datetime = Field(description="Timestamp of the last update")
    created_at: datetime = Field(description="Timestamp when the sensor was created")


class OldServiceTempSensorCreateInfo(BaseModel):
    """
    Data needed to create a new temperature sensor in the old service.
    Corresponds to the SensorCreate struct in the Go codebase.
    """

    name: str = Field(description="Name of the sensor")
    location: str = Field(description="Physical location where the sensor is installed")
    type: str = Field(default="TEMPERATURE", description="Type of the sensor")
    unit: str = Field(default="°C", description="Unit of measurement (e.g., '°C' for Celsius)")
