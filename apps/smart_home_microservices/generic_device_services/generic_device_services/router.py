"""
Интерфейсы FastAPI-роутера для сервиса устройств (для простых устройств и для датчиков).
"""

from typing import Dict, List, Optional, Any, Union
import inspect

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, status as status_codes, Body

from generic_device_services.device_dto import (
    DeviceInfo,
    SensorInfo,
    DeviceSettingsInfo,
    DeviceSettingsFieldInfo,
    MeasurementProcessInfo,
    TelemetrySampleFormat,
)

from telemetry_dto import TelemetrySample


class NotImplementedHttpError(HTTPException):
    def __init__(self, detail: str = "This feature is not yet implemented"):
        super().__init__(status_code=status_codes.HTTP_501_NOT_IMPLEMENTED, detail=detail)


class BaseDeviceRouter(APIRouter):
    """
    Интерфейс FastAPI-роутера для сервиса устройств (датчиков и исполнительных устройств).
    HTTP-маршруты здесь уже прибиты к абстрактным методам.

    Считаем, что у любого устройства есть настройки и статус "работает/не работает".
    Для исполнительных устройств отдельных методов управления не делаем,
    команду на различные действия будем давать через установку соответствующих настроек
    (например, "открыть ворота" будет делаться через /device/{device_id}/set_settings?fld_name=is_opened&fld_value=true)

    """

    def _raise_not_implemented(self):
        """Helper method to raise NotImplementedHttpError with the current method name."""

        method_name = inspect.currentframe().f_back.f_code.co_name
        raise NotImplementedHttpError(f"method {method_name}() should be implemented in child classes!")

    def __init__(self, tags: Optional[List[str]] = None, telemetry_queue_url: Optional[str] = None):
        super().__init__(tags=tags)
        self._telemetry_queue_url = telemetry_queue_url

        @self.get("/health_check")
        async def health_check() -> Optional[bool]:
            return await self.health_check()

        @self.get("/all_devices")
        async def get_devices(available_only: bool = True, active_only: bool = False) -> List[DeviceInfo]:
            return await self.get_devices(available_only=available_only, active_only=active_only)

        @self.post("/device/add")
        async def add_device(payload: Optional[Any] = Body()) -> DeviceInfo:
            return await self.add_device(payload)

        @self.get("/device/{device_id}/info")
        async def get_device_info(device_id: int) -> DeviceInfo:
            return await self.get_device(device_id)

        @self.put("/device/{device_id}/active/{is_active}")
        async def add_device(device_id: int, is_active: bool):
            await self.set_device_active(device_id, is_active)

        @self.put("/device/{device_id}/health_check_interval/{interval}")
        async def set_device_health_check_interval(device_id: int, interval: Optional[float] = None):
            # get_health_check_interval отдельно не делаем, его и в get_device_info можно посмотреть
            await self.set_device_health_check_interval(device_id, interval)

        @self.delete("/device/{device_id}/delete")
        async def delete_device(device_id: int):
            return await self.delete_device(device_id)

        @self.get("/device/{device_id}/settings")
        async def get_device_settings(device_id: int) -> DeviceSettingsInfo:
            return await self.get_device_settings(device_id)

        @self.put("/device/{device_id}/settings/update")
        async def update_device_settings(device_id, new_settings: DeviceSettingsInfo = Body(embed=False)):
            # Допускается неполное обновление (только части полей)
            await self.update_device_settings(device_id, new_settings)

        @self.put("/device/{device_id}/settings/update_field")
        async def update_device_settings_field(device_id, fld_name: str, fld_value: Optional[Any] = Body()):
            await self.update_device_settings_field(device_id, fld_name, fld_value)

        @self.get("device/{device_id}/settings/update_field")
        # debug purposes!
        async def update_device_settings_field(device_id, fld_name: str, fld_value: Optional[Any]):
            await self.update_device_settings_field(device_id, fld_name, fld_value)

        @self.get("/device/{device_id}/settings_schema")
        async def get_device_settings_schema(device_id: int) -> Dict[str, DeviceSettingsFieldInfo]:
            return await self.get_device_settings_schema(device_id)

    ####################################################################################
    # Абстрактные методы для роутера: переопределяем их в классах-реализациях
    ####################################################################################

    async def health_check(self) -> Optional[bool]:
        self._raise_not_implemented()

    async def get_devices(self, available_only: bool = True, active_only: bool = False) -> List[DeviceInfo]:
        """List all registered devices."""
        self._raise_not_implemented()

    async def get_device(self, device_id: int) -> DeviceInfo:
        self._raise_not_implemented()

    async def get_device_settings(self, device_id: int) -> DeviceSettingsInfo:
        self._raise_not_implemented()

    async def add_device(self, payload: Any) -> DeviceInfo:
        self._raise_not_implemented()

    async def delete_device(self, device_id: int):
        self._raise_not_implemented()

    async def set_device_active(self, device_id: int, is_active: bool) -> None:
        self._raise_not_implemented()

    async def set_device_health_check_interval(self, device_id: int, interval: Optional[float]) -> None:
        self._raise_not_implemented()

    async def update_device_settings(self, device_id: int, new_settings: DeviceSettingsInfo) -> None:
        self._raise_not_implemented()

    async def update_device_settings_field(self, device_id: int, fld_name: str, fld_value: Any) -> None:
        self._raise_not_implemented()

    async def get_device_settings_schema(self, device_id: int) -> Dict[str, DeviceSettingsFieldInfo]:
        self._raise_not_implemented()


class BaseSensorRouter(BaseDeviceRouter):
    """
    Болваночка роутера для сервиса датчиков: добавлены методы управления измерениями.

    Нужно собраться с духом, помолиться и реализовать эти абстрактные методы в классах-наследниках...
    """

    def __init__(self, tags: Optional[List[str]] = None):
        super().__init__(tags=tags)

        # Чтобы поддерживалось внутреннее состояние (и объект роутера не пересоздавался при каждом запуске),
        # HTTP-маршруты будем надевать на методы прямо в __init__

        @self.get("/all_devices")
        async def get_devices(
            available_only: bool = True, active_only: bool = False
        ) -> List[Union[SensorInfo, DeviceInfo]]:
            return await self.get_devices(available_only=available_only, active_only=active_only)

        @self.post("/device/add")
        async def add_device(payload: Optional[Any] = Body()) -> Union[SensorInfo, DeviceInfo]:
            return await self.add_device(payload)

        @self.get("/device/{device_id}/info")
        async def get_device(device_id: int) -> Union[SensorInfo, DeviceInfo]:
            return await self.get_device(device_id)

        @self.get("/device/{device_id}/measurement_processes")
        async def get_measurement_processes(
            device_id: Optional[int] = None, active_only: bool = False
        ) -> List[MeasurementProcessInfo]:
            return await self.get_device_measurement_processes(device_id, active_only=active_only)

        @self.get("/measurement_process/{meas_proc_id}")
        async def get_measurement_process(meas_proc_id: int) -> MeasurementProcessInfo:
            return await self.get_measurement_process(meas_proc_id)

        @self.get(path="/device/{device_id}/measure")
        async def measure_once(device_id: int, sample_format: TelemetrySampleFormat) -> TelemetrySample:
            return await self.measure_once(device_id, sample_format)

        @self.post("/device/{device_id}/create_measurement_process", operation_id="create_management_process")
        async def create_measurement_process(
            device_id: int,
            sample_format: Optional[TelemetrySampleFormat] = Body(default=None),
            sampling_interval: Optional[float] = Body(default=None),
        ) -> MeasurementProcessInfo:
            return await self.create_measurement_process(device_id, sample_format, sampling_interval)

        @self.put("/measurement_process/{meas_proc_id}/stop")
        async def stop_measurement_process(meas_proc_id: int):
            return await self.stop_measurement_process(meas_proc_id)

    async def get_devices(
        self, available_only: bool = True, active_only: bool = False
    ) -> List[Union[SensorInfo, DeviceInfo]]:
        """List all registered devices."""
        self._raise_not_implemented()

    async def get_device(self, device_id: int) -> Union[SensorInfo, DeviceInfo]:
        self._raise_not_implemented()

    async def add_device(self, payload: Any) -> Union[SensorInfo, DeviceInfo]:
        self._raise_not_implemented()

    async def get_device_measurement_processes(
        self, device_id: Optional[int], active_only: bool
    ) -> List[MeasurementProcessInfo]:
        self._raise_not_implemented()

    async def get_measurement_process(self, meas_proc_id: int) -> MeasurementProcessInfo:
        self._raise_not_implemented()

    async def create_measurement_process(
        self, device_id: int, sample_format: Optional[TelemetrySampleFormat], sampling_interval: Optional[float]
    ) -> MeasurementProcessInfo:
        self._raise_not_implemented()

    async def stop_measurement_process(self, meas_proc_id: int) -> None:
        self._raise_not_implemented()

    async def measure_once(self, device_id: int, sample_format: TelemetrySampleFormat) -> TelemetrySample:
        self._raise_not_implemented()


# Script entrypoint to run with Uvicorn
if __name__ == "__main__":

    app = FastAPI(title="Smart Home BaseSensorService")
    # Choose the appropriate router
    sensor_router = BaseSensorRouter()
    app.include_router(sensor_router)

    # Launch server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
