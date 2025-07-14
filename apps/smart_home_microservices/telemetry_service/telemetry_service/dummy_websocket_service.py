from typing import AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio

app = FastAPI()


class SensorUpdate(BaseModel):
    sensor_id: int
    temperature: float
    status: str


@app.websocket("/ws/sensor-updates")
async def sensor_updates_ws(websocket: WebSocket) -> AsyncGenerator[SensorUpdate, None]:
    """
    WebSocket endpoint that sends SensorUpdate models as JSON messages.
    Sends a new sensor reading every second.
    """
    await websocket.accept()
    try:
        for idx in range(1, 6):
            update = SensorUpdate(
                sensor_id=idx,
                temperature=20.0 + idx * 0.5,
                status="OK" if idx % 2 == 0 else "WARN",
            )
            await websocket.send_json(update.dict())
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
