from typing import Dict, List, Optional

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel


# Pydantic models
class SensorReading(BaseModel):
    timestamp: str  # ISO format
    value: float


class Sensor(BaseModel):
    id: str
    type: str
    location: str


# Type aliases for internal state
type SensorDict = Dict[str, Sensor]
type ReadingsDict = Dict[str, List[SensorReading]]


class BaseSensorRouter(APIRouter):
    """
    Болваночка роутера для сервиса датчиков.
    HTTP-маршруты здесь прибиты гвоздями к абстрактным методам.
    Нужно реализовать эти абстрактные методы в классах-наследниках -- и будет счастье.
    """

    def __init__(self, tags: Optional[List[str]] = None):
        super().__init__(tags=tags)

        # Здесь поддерживается внутреннее состояние

        @self.get("/hello")
        async def hello():
            return await self.hello()

        @self.get("/sensors")
        async def get_sensors(available_only: bool = True, active_only: bool = False):
            return await self.get_sensors(available_only=available_only, active_only=active_only)

    async def get_sensors(self) -> List[Sensor]:
        """List all registered sensors."""
        raise NotImplementedError("method get_sensors(...) should be implemented in child classes!")

    async def hello(self) -> str:
        return "hello!"


# Example subclass for specialized behavior
class TemperatureSensorRouter(BaseSensorRouter):
    def __init__(self, tags: Optional[List[str]] = None):
        super().__init__(tags=tags)
        # Initialize internal state for sensors and readings
        self._sensors: SensorDict = {}

        # Add some hardcoded temperature sensors
        self._sensors = {
            "temp1": Sensor(id="temp1", type="temperature", location="Living Room"),
            "temp2": Sensor(id="temp2", type="temperature", location="Bedroom"),
            "temp3": Sensor(id="temp3", type="temperature", location="Kitchen"),
        }
        # Initialize empty readings for each sensor
        self._readings = {sensor_id: [] for sensor_id in self._sensors}

    async def add_reading(self, sensor_id: str, reading: SensorReading) -> SensorReading:
        # enforce temperature range
        if reading.value < -50 or reading.value > 150:
            raise HTTPException(status_code=400, detail="Temperature out of range")
        return await super().add_reading(sensor_id, reading)

    async def get_sensors(self, available_only: bool = True, active_only: bool = False) -> List[Sensor]:
        """
        Get a list of all registered sensors.

        Returns:
            List of Sensor objects
        """
        return list(self._sensors.values())

    async def hello(self) -> str:
        return "world!"


# Script entrypoint to run with Uvicorn
if __name__ == "__main__":

    app = FastAPI(title="Smart Home Sensor Service")
    # Choose the appropriate router
    sensor_router = BaseSensorRouter()
    app.include_router(sensor_router)
    # To use the temperature-specific router instead, uncomment below:
    # temp_router = TemperatureSensorRouter()
    # app.include_router(temp_router)

    # Launch server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
