import inspect
import asyncio
import random
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Union, AsyncGenerator

import uvicorn
from fastapi import FastAPI, APIRouter, HTTPException, status as status_codes, WebSocket, WebSocketDisconnect


from telemetry_dto import MeasurementProcessInfo, TelemetrySampleInfo, FloatTelemetrySampleInfo, StatusEvent


class NotImplementedHttpError(HTTPException):
    def __init__(self, detail: str = "This feature is not yet implemented"):
        super().__init__(status_code=status_codes.HTTP_501_NOT_IMPLEMENTED, detail=detail)


class BaseTelemetryRouter(APIRouter):
    """
    Базовый абстрактный роутер для работы с телеметрией.
    Декларирует HTTP-эндпоинты, также декларирует WebSocket-эндпоинты и Kafka-подписки.
    """

    def __init__(self, telemetry_queue_url: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._telemetry_queue_url = telemetry_queue_url

        @self.get("/health_check")
        async def health_check() -> Optional[bool]:
            """Проверка состояния сервиса"""
            return await self.health_check()

        @self.get("/measurement_processes", operation_id="get_measurement_processes")
        async def get_measurement_processes(
            sensor_ids: Optional[Union[int, List[int]]] = None,
            sensor_uuids: Optional[Union[UUID, List[UUID]]] = None,
            active_only: bool = False,
            min_start_ts: Optional[datetime] = None,
            max_start_ts: Optional[datetime] = None,
        ) -> List[MeasurementProcessInfo]:
            """
            Вернуть все процессы измерений, которые обрабатывал этот сервис
            (с возможностью фильтрации по датчикам и времени запуска).
            """
            return await self.get_measurement_processes(
                sensor_ids=sensor_ids,
                sensor_uuids=sensor_uuids,
                active_only=active_only,
                min_start_ts=min_start_ts,
                max_start_ts=max_start_ts,
            )

        @self.get("/measurement_process/{meas_proc_id}")
        async def get_measurement_process(meas_proc_id: int) -> MeasurementProcessInfo:
            """
            Вернуть информацию об отдельном процессе измерений по его ID
            """
            return await self.get_measurement_process(meas_proc_id)

        @self.get("/measurement_process/{meas_proc_id}/samples")
        async def get_samples(
            meas_proc_id: int, start_ts: Optional[datetime] = None, end_ts: Optional[datetime] = None
        ) -> List[TelemetrySampleInfo]:
            """
            Достать из БД все измерения для конкретного процесса.
            Опционально -- можно извлечь не все измерения, а только в заданном диапазоне времени.
            """
            return await self.get_samples(meas_proc_id=meas_proc_id, start_ts=start_ts, end_ts=end_ts)

        @self.websocket("/measurement_process/{meas_proc_id}/stream")
        async def stream_samples(meas_proc_id: int, websocket: WebSocket) -> AsyncGenerator[TelemetrySampleInfo, None]:
            """
            Передавать по вебсокету новые измерения для заданного процесса измерений (в виде JSON-объектов).
            Нужно для обновляемых виджетов в дэшбордах веб-интерфейса.
            """
            await websocket.accept()
            try:
                async for update in self.stream_samples(meas_proc_id):
                    await websocket.send_json(update.dict())
            except WebSocketDisconnect:
                print("Client disconnected")
            finally:
                await websocket.close()

    def _raise_not_implemented(self):
        """Helper method to raise NotImplementedHttpError with the current method name."""

        method_name = inspect.currentframe().f_back.f_code.co_name
        raise NotImplementedHttpError(f"method {method_name}() should be implemented in child classes!")

    async def get_measurement_processes(
        self,
        sensor_ids: Optional[Union[int, List[int]]] = None,
        sensor_uuids: Optional[Union[UUID, List[UUID]]] = None,
        active_only: bool = False,
        min_start_ts: Optional[datetime] = None,
        max_start_ts: Optional[datetime] = None,
    ) -> List[MeasurementProcessInfo]:
        self._raise_not_implemented()

    async def get_measurement_process(self, meas_proc_id: int) -> MeasurementProcessInfo:
        self._raise_not_implemented()

    async def get_samples(
        self, meas_proc_id: int, start_ts: Optional[datetime] = None, end_ts: Optional[datetime] = None
    ) -> List[TelemetrySampleInfo]:
        self._raise_not_implemented()

    async def example_stream_samples(self, meas_proc_id: int) -> AsyncGenerator[FloatTelemetrySampleInfo, None]:
        """
        Stream random FloatTelemetrySampleInfo objects with some interval.

        Args:
            meas_proc_id: ID of the measurement process

        Yields:
            FloatTelemetrySampleInfo: Randomly generated telemetry samples
        """

        interval: float = 1.0
        n_samples: int = 20
        for i in range(n_samples):
            try:
                # Generate a random float value between 0.0 and 100.0
                random_value = random.uniform(0.0, 100.0)

                # Create a new sample with current timestamp
                sample = FloatTelemetrySampleInfo(timestamp=datetime.now().astimezone(), value=random_value)

                yield sample

                # Wait for the specified interval before generating the next sample
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                # Handle cancellation gracefully
                break
            except Exception as e:
                # Log any other errors and stop the stream
                print(f"Error in stream_samples: {e}")
                break

    async def stream_samples(self) -> AsyncGenerator[TelemetrySampleInfo, None]:
        self._raise_not_implemented()

    async def _process_status_event(self, event: StatusEvent):
        """
        Обработка обновлений статуса устройства, прилетающих из kafka-очереди telemetry_status_events.

        Обработка зависит от типа события (например, подписаться на новый топик в Kafka,
        когда начался процесс измерений на датчике).

        **Это абстрактный метод, его нужно переопределить в дочернем классе!**
        """
        self._raise_not_implemented()

    async def _process_sample(self, topic_name: str, event: TelemetrySampleInfo):
        """
        Обработка отдельных сообщений, извлечённых из Kafka-очереди с данными для заданного процесса измерений.
        Процесс измерений определяем по topic_name.

        **Это абстрактный метод, его нужно переопределить в дочернем классе!**
        """
        self._raise_not_implemented()


if __name__ == "__main__":

    app = FastAPI(title="Telemetry Service", description="Сервис телеметрии: абстрактный роутер")

    router = BaseTelemetryRouter()
    app.include_router(router)

    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
