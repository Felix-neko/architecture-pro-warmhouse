"""
Настройки сервиса, подгружаемые из переменных среды
"""

from pydantic import BaseSettings


class ServiceSettings(BaseSettings):
    old_service_url: str = "localhost:8080"

    host: str = "0.0.0.0"
    port: int = 8000


settings = ServiceSettings()
