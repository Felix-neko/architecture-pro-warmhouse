# First stage: copy all required files
FROM python:3.12-slim as old_system_sensor_service

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m pip install --upgrade pip uv


COPY ./old_system_sensor_service /app/old_system_sensor_service

# По-правильному все библиотеки-зависимости надо было залить в PyPi-репозиторий
# и указать как зависимости PIP-пакета old_system_sensor_service, но но PyPi-репу я быстро не разверну,
# так что делаем по-крестьянски ))
COPY ./generic_device_services /app/generic_device_services
COPY ./telemetry_dto /app/telemetry_dto


WORKDIR /app

# Create a non-root user
RUN useradd -m appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set working directory
WORKDIR /app/old_system_sensor_service

# Install dependencies

RUN uv sync
RUN uv pip install -e ../generic_device_services && \
    uv pip install -e ../telemetry_dto

EXPOSE 8000

CMD ["uv", "run", "--python", "3.12", "/app/old_system_sensor_service/old_system_sensor_service/main.py"]

# Sleep for 10 hours (useful for debugging)
#CMD ["sleep", "36000"]