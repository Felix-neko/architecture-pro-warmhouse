"""
Настройки сервиса, подгружаемые из переменных среды
"""

from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    # На каком хосту и порту запускать наш сервис
    host: str = "0.0.0.0"
    port: int = 8000

    # Где живёт старый сервис, из которого мы берём данные
    old_service_url: str = "http://localhost:8080"


settings = ServiceSettings()
