from fastapi import FastAPI
import uvicorn


from old_system_sensor_service.router import OldSystemTempSensorRouter
from old_system_sensor_service.settings import settings


# Script entrypoint to run with Uvicorn
if __name__ == "__main__":

    app = FastAPI(title="Old System Temperature Sensor Adapter")
    # Choose the appropriate router
    sensor_router = OldSystemTempSensorRouter(old_service_url=settings.old_service_url)
    app.include_router(sensor_router)

    # Launch server on port 8000
    uvicorn.run(app, host=settings.host, port=settings.port)
