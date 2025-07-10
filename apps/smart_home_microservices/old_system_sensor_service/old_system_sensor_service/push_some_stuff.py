import asyncio
from old_system_sensor_service.telemetry_queue_processor import push_some_events


if __name__ == "__main__":
    # Uncomment any of these to test different functionality
    asyncio.run(push_some_events())
    # asyncio.run(push_telemetry_samples())
    print("SOME EVENTS PUSHED!")
