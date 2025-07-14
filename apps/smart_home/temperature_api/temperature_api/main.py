
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import random

app = FastAPI(title="Temperature API",
             description="A simple API to get temperature data",
             version="1.0.0")

SENSOR_LOCATIONS = {
    "1": "Living Room",
    "2": "Bedroom",
    "3": "Kitchen"
}

LOCATION_SENSORS = {v: k for k, v in SENSOR_LOCATIONS.items()}


class TemperatureResponse(BaseModel):
    value: float = Field(description="Measured temperature value.")
    unit: str = Field(description="Unit of measurement (e.g., Celsius).")
    timestamp: datetime = Field(description="Timestamp when the measurement was taken.")
    location: str = Field(description="Location where the temperature was measured.")
    status: str = Field(description="Sensor status (e.g., active, inactive).")
    sensor_id: str = Field(description="Unique identifier of the sensor.")
    sensor_type: str = Field(description="Type of the sensor (e.g., temp, pressure, CO2, etc.")
    description: str = Field(description="Additional information about the sensor.")


@app.get("/{sensor_id}/temperature/{location}")
@app.get("/{sensor_id}/temperature")
@app.get("/temperature/{location}")
@app.get("/temperature")
async def get_temperature(
    sensor_id: str = "",
    location: str = ""
) -> TemperatureResponse:
    """
    Get temperature for a specific sensor and/or location.
    
    - If no location is provided, it will be determined based on sensor ID
    - If no sensor ID is provided, it will be determined based on location
    - If neither is provided, defaults will be used
    """
    # Determine location based on sensor ID if not provided
    if not location and sensor_id:
        location = SENSOR_LOCATIONS.get(sensor_id, "Unknown")
    
    # Determine sensor ID based on location if not provided
    if not sensor_id and location:
        sensor_id = LOCATION_SENSORS.get(location, "0")
    
    # If still no location or sensor ID, use defaults
    if not location and not sensor_id:
        sensor_id = "0"
        location = "Unknown"
    elif not location:
        location = "Unknown"
    elif not sensor_id:
        sensor_id = "0"
    
    return TemperatureResponse(
        value=round(random.uniform(1, 100), 2),
        unit="°C",
        timestamp=datetime.now().astimezone(),
        location=location,
        status="active",
        sensor_id=sensor_id,
        sensor_type="temperature",
        description=f"Dummy temperature sensor"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
