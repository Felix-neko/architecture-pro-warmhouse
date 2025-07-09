from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import random
from typing import Optional

SENSOR_ID = "SENSOR-4241"

app = FastAPI(title="Temperature API",
             description="A simple API to get temperature data",
             version="1.0.0")

class TemperatureResponse(BaseModel):
    value: float = Field(description="Measured temperature value.")
    unit: str = Field(description="Unit of measurement (e.g., Celsius).")
    timestamp: datetime = Field(description="Timestamp when the measurement was taken.")
    location: str = Field(description="Location where the temperature was measured.")
    status: str = Field(description="Sensor status (e.g., active, inactive).")
    sensor_id: str = Field(description="Unique identifier of the sensor.")
    sensor_type: str = Field(description="Type of the sensor (e.g., temp, pressure, CO2, etc.")
    description: str = Field(description="Additional information about the sensor.")

@app.get("/temperature")
async def get_temperature(location: str) -> TemperatureResponse:
    if not location:
        raise HTTPException(status_code=400, detail="Location parameter is required")
    
    return TemperatureResponse(
        value=round(random.uniform(1, 100), 2),
        unit="°C",
        timestamp=datetime.now(),
        location=location,
        status="active",
        sensor_id=SENSOR_ID,
        sensor_type="temperature",
        description=f"Dummy temperature sensor"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
