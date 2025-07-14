import os
import asyncio
import time
import struct

from aiohttp import web
from aiokafka import AIOKafkaProducer

KAFKA_URL = os.getenv("KAFKA_URL", "localhost:9092")

_tasks = {}

async def poll_sensor(sensor_id: str, freq_hz: float, producer: AIOKafkaProducer, topic: str):
    """Polls a (dummy) sensor at freq_hz and sends raw float readings to Kafka."""
    interval = 1.0 / freq_hz
    next_time = time.perf_counter()
    while True:
        # --- simulate sensor read (replace with real call) ---
        reading: float = get_sensor_reading(sensor_id)
        # pack as big-endian float
        payload = struct.pack('!f', reading)
        await producer.send_and_wait(topic, payload)

        # schedule next iteration precisely
        next_time += interval
        sleep = next_time - time.perf_counter()
        if sleep > 0:
            await asyncio.sleep(sleep)
        else:
            next_time = time.perf_counter()

async def start_polling(request):
    app = request.app
    if app["running"]:
        return web.json_response({"status": "already running"})

    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_URL)
    await producer.start()
    app["producer"] = producer

    _tasks['s1'] = asyncio.create_task(poll_sensor("1", 1000.0, producer, "sensor1"))
    _tasks['s2'] = asyncio.create_task(poll_sensor("2", 1500.0, producer, "sensor2"))
    app["running"] = True
    return web.json_response({"status": "started"})

async def stop_polling(request):
    app = request.app
    if not app["running"]:
        return web.json_response({"status": "not running"})

    for t in _tasks.values():
        t.cancel()
    await asyncio.gather(*_tasks.values(), return_exceptions=True)
    _tasks.clear()

    await app["producer"].stop()
    app["running"] = False
    return web.json_response({"status": "stopped"})

async def on_shutdown(app):
    if app["running"]:
        for t in _tasks.values():
            t.cancel()
        await asyncio.gather(*_tasks.values(), return_exceptions=True)
        await app["producer"].stop()

# Dummy sensor read function

def get_sensor_reading(sensor_id: str) -> float:
    """Stub: replace with actual sensor interfacing code."""
    # e.g., return sensor_lib.read(sensor_id)
    import random
    return random.uniform(0.0, 100.0)


def main():
    app = web.Application()
    app["running"] = False
    app.router.add_get("/start", start_polling)
    app.router.add_get("/stop", stop_polling)
    app.on_shutdown.append(on_shutdown)

    web.run_app(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()