"""
FastAPI-роутер для управления датчиками (роутер-адаптер для старого монолита)
"""

import json
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from collections import defaultdict

import aiohttp
from fastapi import HTTPException, status as status_codes
from pydantic import parse_obj_as
from pydantic.fields import PydanticUndefined

from generic_device_services.router import BaseSensorRouter, SensorInfo, DeviceInfo
from generic_device_services.router import NotImplementedHttpError
from generic_device_services.device_dto import DeviceType, SensorType, DeviceParamInfo, DeviceParamDataType

from old_system_sensor_service.settings import settings
from old_system_sensor_service.old_service_dto import OldServiceTempSensorInfo, OldServiceTempSensorCreateInfo


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

    def _convert_to_sensor_info(self, old_sensor_info: OldServiceTempSensorInfo) -> SensorInfo:
        """Convert OldServiceTempSensorInfo to SensorInfo.

        Args:
            old_sensor_info: The sensor data from the old service

        Returns:
            SensorInfo: The converted sensor information
        """
        return SensorInfo(
            device_id=old_sensor_info.id,
            device_uuid=self._sensor_uuids[old_sensor_info.id],
            name=old_sensor_info.name,
            display_name=f"{old_sensor_info.name}\nLocation: {old_sensor_info.location}",
            sensor_type=SensorType.TEMPERATURE,
            needs_polling=True,
            model_name=None,
            is_active=old_sensor_info.status.lower() == "active",
            is_alive=old_sensor_info.status.lower() == "active",
        )

    async def get_device(self, device_id: int) -> SensorInfo:
        """Get information about a specific sensor by its ID.

        Args:
            device_id: The ID of the sensor to retrieve

        Returns:
            SensorInfo if the sensor is found, None otherwise

        Raises:
            OldServiceNotWorking: If there's an error communicating with the old service
        """
        try:
            url = f"{self._old_service_url}/api/v1/sensors/{device_id}"
            timeout = aiohttp.ClientTimeout(total=self._request_timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == status_codes.HTTP_200_OK:
                        sensor_data = await response.json()
                        sensor = OldServiceTempSensorInfo(**sensor_data)
                        return self._convert_to_sensor_info(sensor)
                    elif response.status == status_codes.HTTP_404_NOT_FOUND:
                        raise HTTPException(
                            status_code=status_codes.HTTP_404_NOT_FOUND,
                            detail=f"Sensor with ID {device_id} not found",
                        )
                    else:
                        error_detail = await response.text()
                        raise OldServiceNotWorking(f"Old service returned status {response.status}: {error_detail}")
        except aiohttp.ClientError as e:
            raise OldServiceNotWorking(f"Failed to connect to old service: {str(e)}")
        except json.JSONDecodeError as ex:
            raise OldServiceNotWorking(f"Old service returned invalid JSON response: {ex}")
        except Exception as e:
            raise OldServiceNotWorking(f"Unexpected error: {str(e)}")

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
                                self._convert_to_sensor_info(sensor) for sensor in old_service_sensors
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

    async def create_device(self, params: Dict[str, Any]) -> SensorInfo:
        """
        Create a new temperature sensor in the old service.

        Args:
            params: Dictionary containing sensor creation data

        Returns:
            SensorInfo: Information about the created sensor

        Raises:
            OldServiceNotWorking: If there's an error communicating with the old service
            HTTPException: If the sensor creation fails
        """
        try:
            # Create sensor data from params
            sensor_data = OldServiceTempSensorCreateInfo(**params)

            # Prepare request to old service
            url = f"{self._old_service_url}/api/v1/sensors"
            timeout = aiohttp.ClientTimeout(total=self._request_timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url, json=sensor_data.dict(), headers={"Content-Type": "application/json"}
                ) as response:

                    if response.status == status_codes.HTTP_201_CREATED:
                        created_sensor_raw = await response.json()
                        sensor = OldServiceTempSensorInfo(**created_sensor_raw)

                        return self._convert_to_sensor_info(sensor)
                    else:
                        error_detail = await response.text()
                        raise OldServiceNotWorking(
                            f"Failed to create sensor. Status: {response.status}, Detail: {error_detail}"
                        )

        except aiohttp.ClientError as e:
            raise OldServiceNotWorking(f"Failed to connect to old service: {str(e)}")
        except json.JSONDecodeError as ex:
            raise OldServiceNotWorking(f"Old service returned invalid JSON response: {ex}")
        except Exception as e:
            raise OldServiceNotWorking(f"Unexpected error: {str(e)}")

    async def delete_device(self, device_id: str):
        """
        Delete a sensor from the old service.

        Args:
            device_id: The ID of the sensor to delete

        Raises:
            OldServiceNotWorking: If there's an error communicating with the old service
            HTTPException: If the sensor is not found or deletion fails
        """
        try:
            url = f"{self._old_service_url}/api/v1/sensors/{device_id}"
            timeout = aiohttp.ClientTimeout(total=self._request_timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.delete(url) as response:
                    if response.status == status_codes.HTTP_200_OK:
                        # Remove the UUID mapping if it exists
                        del self._sensor_uuids[device_id]
                        return
                    elif response.status == status_codes.HTTP_404_NOT_FOUND:
                        raise HTTPException(
                            status_code=status_codes.HTTP_404_NOT_FOUND,
                            detail=f"Sensor with ID {device_id} not found",
                        )
                    else:
                        error_detail = await response.text()
                        raise OldServiceNotWorking(
                            f"Failed to delete sensor. Status: {response.status}, Detail: {error_detail}"
                        )
        except HTTPException as e:  # Re-raise HTTPException
            raise e
        except aiohttp.ClientError as e:
            raise OldServiceNotWorking(f"Failed to connect to old service: {str(e)}")
        except Exception as e:
            raise OldServiceNotWorking(f"Unexpected error: {str(e)}")

    async def get_device_creation_params(self) -> Dict[str, DeviceParamInfo]:
        """
        Get the parameters required to create a new temperature sensor in the old service.
        Automatically extracts field information from OldServiceTempSensorCreateInfo.

        Returns:
            Dictionary mapping parameter names to their metadata.
        """
        param_info = {}

        for field_name, field in OldServiceTempSensorCreateInfo.model_fields.items():
            # Get field type and handle it appropriately
            field_type = field.annotation
            data_type = DeviceParamDataType.TEXT  # Default to TEXT

            if field_type in (int, float):
                data_type = DeviceParamDataType.INT if field_type is int else DeviceParamDataType.FLOAT

            # Check if field has choices (enum)
            allowed_values = None
            if hasattr(field_type, "__args__") and field_type.__args__:
                allowed_values = list(field_type.__args__)

            # Get default value if exists
            default_value = field.default if field.default is not PydanticUndefined else None

            param_info[field_name] = DeviceParamInfo(
                name=field_name,
                display_name=field_name.replace("_", " ").title(),
                description=field.description or f"{field_name} parameter",
                required=field.default is PydanticUndefined and field.default_factory is None,
                data_type=data_type,
                default_value=default_value,
                allowed_values=allowed_values,
            )

        return param_info
