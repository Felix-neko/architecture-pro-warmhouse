from typing import Optional, List

from generic_device_services.router import BaseSensorRouter, SensorInfo
from generic_device_services.device_dto import SensorType


# Example subclass for specialized behavior
class OldSystemTempSensorRouter(BaseSensorRouter):
    def __init__(self, tags: Optional[List[str]] = None):
        super().__init__(tags=tags)
        # Initialize internal state for sensors


        # Add some hardcoded temperature sensors using SensorInfo
        self._sensors = {
            1: SensorInfo(
                device_id=1,
                name="Living Room Temperature",
                display_name="Living Room",
                type=SensorType.TEMPERATURE,
                model_name="DS18B20",
                is_active=True,
                is_alive=True,
                min_sampling_interval=1.0,
            ),
            2: SensorInfo(
                device_id=2,
                name="Bedroom Temperature",
                display_name="Bedroom",
                type=SensorType.TEMPERATURE,
                model_name="DS18B20",
                is_active=True,
                is_alive=True,
                min_sampling_interval=1.0,
            ),
            3: SensorInfo(
                device_id=3,
                name="Kitchen Temperature",
                display_name="Kitchen",
                type=SensorType.TEMPERATURE,
                model_name="DS18B20",
                is_active=True,
                is_alive=True,
                min_sampling_interval=1.0,
            ),
        }
        # Initialize empty readings for each sensor
        self._readings = {sensor_id: [] for sensor_id in self._sensors}

    async def get_sensors(self, available_only: bool = True, active_only: bool = False) -> List[SensorInfo]:
        """Get a list of all registered temperature sensors."""
        sensors = list(self._sensors.values())

        if available_only:
            sensors = [s for s in sensors if s.is_active and s.is_alive]

        if active_only:
            sensors = [s for s in sensors if self._readings.get(s.device_id)]

        return sensors

    async def hello(self) -> str:
        return "Temperature sensor service is running!"

