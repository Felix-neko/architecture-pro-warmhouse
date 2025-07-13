import json
from typing import Optional, List, Dict
from uuid import UUID, uuid4
from collections import defaultdict

import aiohttp
from fastapi import HTTPException, status as status_codes
from pydantic import parse_obj_as

from generic_device_services.router import BaseSensorRouter, SensorInfo
from generic_device_services.router import NotImplementedHttpError

from old_system_sensor_service.settings import settings
from old_system_sensor_service.dto import OldServiceTempSensorInfo


class OldServiceNotWorking(HTTPException):
    def __init__(self, detail: str = "Old service is not working properly!"):
        super().__init__(status_code=status_codes.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


# Example subclass for specialized behavior
class OldSystemTempSensorRouter(BaseSensorRouter):
    def __init__(self, tags: Optional[List[str]] = None, old_service_url: Optional[str] = settings.old_service_url):
        super().__init__(tags=tags)
        # Initialize internal state for sensors
        self._old_service_url = old_service_url
        self._request_timeout = 2
        self._sensor_uuids: Dict[int, UUID] = defaultdict(uuid4)

        # Add some hardcoded temperature sensors using SensorInfo
        # self._sensors = {
        #     1: SensorInfo(
        #         device_id=1,
        #         name="Living Room Temperature",
        #         display_name="Living Room",
        #         type=SensorType.TEMPERATURE,
        #         model_name="DS18B20",
        #         is_active=True,
        #         is_alive=True,
        #         min_sampling_interval=1.0,
        #     ),
        #     2: SensorInfo(
        #         device_id=2,
        #         name="Bedroom Temperature",
        #         display_name="Bedroom",
        #         type=SensorType.TEMPERATURE,
        #         model_name="DS18B20",
        #         is_active=True,
        #         is_alive=True,
        #         min_sampling_interval=1.0,
        #     ),
        #     3: SensorInfo(
        #         device_id=3,
        #         name="Kitchen Temperature",
        #         display_name="Kitchen",
        #         type=SensorType.TEMPERATURE,
        #         model_name="DS18B20",
        #         is_active=True,
        #         is_alive=True,
        #         min_sampling_interval=1.0,
        #     ),
        # }
        # Initialize empty readings for each sensor
        # self._readings = {sensor_id: [] for sensor_id in self._sensors}

    # async def get_sensors(self, available_only: bool = True, active_only: bool = False) -> List[SensorInfo]:
    #     """Get a list of all registered temperature sensors."""
    #     sensors = list(self._sensors.values())
    #
    #     if available_only:
    #         sensors = [s for s in sensors if s.is_active and s.is_alive]
    #
    #     if active_only:
    #         sensors = [s for s in sensors if self._readings.get(s.device_id)]
    #
    #     return sensors

    async def hello(self) -> str:
        return "Temperature sensor service is running!"

    async def health_check(self) -> Optional[bool]:
        url = f"{self._old_service_url}/health"
        timeout = aiohttp.ClientTimeout(total=self._request_timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == status_codes.HTTP_200_OK:
                        data = await response.json()
                        if isinstance(data, dict) and data.get("status") == "ok":
                            return True
                        else:
                            raise OldServiceNotWorking(f"Old service health check returned unexpected response: {data}")
                    else:
                        raise OldServiceNotWorking(f"Old service returned status code: {response.status}")
        except aiohttp.ClientError as e:
            raise OldServiceNotWorking(f"Failed to connect to old service: {str(e)}")
        except json.JSONDecodeError as ex:
            raise OldServiceNotWorking(f"Old service returned invalid JSON response {ex}")
        except Exception as e:
            raise OldServiceNotWorking(f"Unexpected error during health check: {str(e)}")

    async def get_device(self, device_id: int) -> Optional[SensorInfo]:
        """Get information about a specific sensor by its ID.

        Args:
            device_id: The ID of the sensor to retrieve

        Returns:
            SensorInfo if the sensor is found, None otherwise

        Raises:
            OldServiceNotWorking: If there's an error communicating with the old service
        """
        url = f"{self._old_service_url}/api/v1/sensors/{device_id}"
        timeout = aiohttp.ClientTimeout(total=self._request_timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        sensor_data = await response.json()
                        try:
                            sensor = OldServiceTempSensorInfo(**sensor_data)
                            return SensorInfo(
                                device_id=sensor.id,
                                name=sensor.name,
                                device_uuid=self._sensor_uuids[sensor.id],
                                needs_polling=True,
                                model_name=None,
                                is_active=sensor.status.lower() == "active",
                                is_alive=sensor.status.lower() == "active",
                            )
                        except (TypeError, ValueError) as e:
                            raise OldServiceNotWorking(
                                f"Failed to parse sensor data from old service: {str(e)}\n"
                                f"Received data: {sensor_data}"
                            )
                    elif response.status == status_codes.HTTP_404_NOT_FOUND:
                        raise HTTPException(
                            status_code=status_codes.HTTP_404_NOT_FOUND, detail=f"Sensor with ID {device_id} not found"
                        )
                    else:
                        raise OldServiceNotWorking(f"Old service returned status code: {response.status}")
        except aiohttp.ClientError as e:
            raise OldServiceNotWorking(f"Failed to connect to old service: {str(e)}")
        except json.JSONDecodeError as ex:
            raise OldServiceNotWorking(f"Old service returned invalid JSON response: {ex}")

    async def get_devices(self, available_only: bool = True, active_only: bool = False) -> List[SensorInfo]:
        """Get a list of all registered temperature sensors."""
        url = f"{self._old_service_url}/api/v1/sensors"
        timeout = aiohttp.ClientTimeout(total=self._request_timeout)

        if not available_only:
            raise NotImplementedHttpError("available_only=False key is not supported for this router!")
        if active_only:
            raise NotImplementedHttpError("active_only=True key is not supported for this router!")

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == status_codes.HTTP_200_OK:
                        in_data = await response.json()
                        if not in_data:
                            return []
                        try:
                            # Parse the list of sensors from the old service
                            old_service_sensors = parse_obj_as(List[OldServiceTempSensorInfo], in_data)

                            # Convert old service sensors to new SensorInfo objects
                            new_service_sensors = [
                                SensorInfo(
                                    device_id=sensor.id,
                                    name=sensor.name,
                                    device_uuid=self._sensor_uuids[
                                        sensor.id
                                    ],  # Automatically generates UUID for new IDs
                                    needs_polling=True,
                                    model_name=None,
                                    is_active=sensor.status.lower() == "active",
                                    is_alive=sensor.status.lower() == "active",
                                )
                                for sensor in old_service_sensors
                            ]
                            return new_service_sensors
                        except (TypeError, ValueError) as e:
                            raise OldServiceNotWorking(
                                f"Failed to parse sensor data from old service: {str(e)}\n Received data: {in_data}"
                            )
                    else:
                        raise OldServiceNotWorking(f"Old service returned status code: {response.status}")
        except aiohttp.ClientError as e:
            raise OldServiceNotWorking(f"Failed to connect to old service: {str(e)}")
        except json.JSONDecodeError as ex:
            raise OldServiceNotWorking(f"Old service returned invalid JSON response {ex}")
