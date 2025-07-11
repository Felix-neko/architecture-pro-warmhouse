from typing import Dict, List, Optional, Any
import inspect

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, status as status_codes, Body

from generic_sensor_service.sensor_dto import (
    SensorInfo,
    SensorSettingsInfo,
    SensorSettingsFieldInfo,
    MeasurementProcessInfo,
    TelemetrySampleFormat,
)


class NotImplementedHttpError(HTTPException):
    def __init__(self, detail: str = "This feature is not yet implemented"):
        super().__init__(status_code=status_codes.HTTP_501_NOT_IMPLEMENTED, detail=detail)


class BaseSensorRouter(APIRouter):
    """
    Болваночка роутера для сервиса датчиков.
    HTTP-маршруты здесь уже прибиты к абстрактным методам.
    Нужно собраться с духом, помолиться и реализовать эти абстрактные методы в классах-наследниках...
    """

    def __init__(self, tags: Optional[List[str]] = None):
        super().__init__(tags=tags)

        # Чтобы поддерживалось внутреннее состояние (и объект роутера не пересоздавался при каждом запуске),
        # HTTP-маршруты будем надевать на методы прямо в __init__

        @self.get("/all_sensors")
        async def get_sensors(available_only: bool = True, active_only: bool = False) -> List[SensorInfo]:
            return await self.get_sensors(available_only=available_only, active_only=active_only)

        @self.post("/sensor/add")
        async def add_sensor(payload: Optional[Any] = Body()) -> SensorInfo:
            return await self.add_sensor(payload)

        @self.put("/sensor/{sensor_id}/active/{is_active}")
        async def add_sensor(sensor_id: int, is_active: bool):
            await self.set_sensor_active(sensor_id, is_active)

        @self.put("/sensor/{sensor_id}/health_check_interval/{interval}")
        async def set_sensor_health_check_interval(sensor_id: int, interval: Optional[float] = None):
            # get_health_check_interval отдельно не делаем, его и в get_sensor_info можно посмотреть
            await self.set_sensor_health_check_interval(sensor_id, interval)

        @self.delete("/sensor/{sensor_id}/delete")
        async def delete_sensor(sensor_id: int):
            return await self.delete_sensor(sensor_id)

        @self.get("/sensor/{sensor_id}/info")
        async def get_sensor_info(sensor_id: int) -> SensorInfo:
            return await self.get_sensor_info(sensor_id)

        @self.get("/sensor/{sensor_id}/settings")
        async def get_sensor_settings(sensor_id: int) -> SensorSettingsInfo:
            return await self.get_sensor_settings(sensor_id)

        @self.put("/sensor/{sensor_id}/settings/update")
        async def update_sensor_settings(sensor_id, new_settings: SensorSettingsInfo = Body(embed=False)):
            # Допускается неполное обновление (только части полей!)
            await self.update_sensor_settings(sensor_id, new_settings)

        # @self.put("/sensor/{sensor_id}/settings/update_field")
        # async def update_sensor_settings_field(sensor_id, fld_name: str, fld_value: Optional[Any] = Body()):
        #     await self.update_sensor_settings_field(sensor_id, fld_name, fld_value)

        @self.get("/sensor/{sensor_id}/settings_schema")
        async def get_sensor_settings_schema(sensor_id: int) -> Dict[str, SensorSettingsFieldInfo]:
            return await self.get_sensor_settings_schema(sensor_id)

        @self.get("/sensor/{sensor_id}/measurement_processes")
        async def get_measurement_processes(
            sensor_id: Optional[int] = None, active_only: bool = False
        ) -> List[MeasurementProcessInfo]:
            return await self.get_sensor_measurement_processes(sensor_id, active_only=active_only)

        @self.get("/measurement_process/{meas_proc_id}")
        async def get_measurement_process(meas_proc_id: int) -> MeasurementProcessInfo:
            return await self.get_measurement_process(meas_proc_id)

        @self.post("/sensor/{sensor_id}/create_measurement_process", operation_id="create_management_process")
        async def create_measurement_process(
            sensor_id: int,
            sample_format: Optional[TelemetrySampleFormat] = Body(default=None),
            sampling_interval: Optional[float] = Body(default=None),
        ) -> MeasurementProcessInfo:
            return await self.create_measurement_process(sensor_id, sample_format, sampling_interval)

        @self.put("/measurement_process/{meas_proc_id}/stop")
        async def stop_measurement_process(meas_proc_id: int):
            return await self.stop_measurement_process(meas_proc_id)

    def _raise_not_implemented(self):
        """Helper method to raise NotImplementedHttpError with the current method name."""

        method_name = inspect.currentframe().f_back.f_code.co_name
        raise NotImplementedHttpError(f"method {method_name}() should be implemented in child classes!")

    ####################################################################################
    # Абстрактные методы для роутера: переопределяем их в классах-реализациях
    ####################################################################################

    async def get_sensors(self, available_only: bool = True, active_only: bool = False) -> List[SensorInfo]:
        """List all registered sensors."""
        self._raise_not_implemented()

    async def get_sensor_info(self, sensor_id: int) -> SensorInfo:
        self._raise_not_implemented()

    async def get_sensor_settings(self, sensor_id: int) -> SensorSettingsInfo:
        self._raise_not_implemented()

    async def add_sensor(self, payload: Any) -> SensorInfo:
        self._raise_not_implemented()

    async def delete_sensor(self, sensor_id: int):
        self._raise_not_implemented()

    async def set_sensor_active(self, sensor_id: int, is_active: bool) -> None:
        self._raise_not_implemented()

    async def set_sensor_health_check_interval(self, sensor_id: int, interval: Optional[float]) -> None:
        self._raise_not_implemented()

    async def update_sensor_settings(self, sensor_id: int, new_settings: SensorSettingsInfo) -> None:
        self._raise_not_implemented()

    async def update_sensor_settings_field(self, sensor_id: int, fld_name: str, fld_value: Any) -> None:
        self._raise_not_implemented()

    async def get_sensor_settings_schema(self, sensor_id: int) -> Dict[str, SensorSettingsFieldInfo]:
        self._raise_not_implemented()

    async def get_sensor_measurement_processes(
        self, sensor_id: Optional[int], active_only: bool
    ) -> List[MeasurementProcessInfo]:
        self._raise_not_implemented()

    async def get_measurement_process(self, meas_proc_id: int) -> MeasurementProcessInfo:
        self._raise_not_implemented()

    async def create_measurement_process(
        self, sensor_id: int, sample_format: Optional[TelemetrySampleFormat], sampling_interval: Optional[float]
    ) -> MeasurementProcessInfo:
        self._raise_not_implemented()

    async def stop_measurement_process(self, meas_proc_id: int) -> None:
        self._raise_not_implemented()


# Script entrypoint to run with Uvicorn
if __name__ == "__main__":

    app = FastAPI(title="Smart Home BaseSensorService")
    # Choose the appropriate router
    sensor_router = BaseSensorRouter()
    app.include_router(sensor_router)

    # Launch server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
