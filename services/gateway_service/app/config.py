import json
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NACOS_ENABLED: bool = True
    NACOS_SERVER_ADDR: str = "nacos:8848"
    NACOS_NAMESPACE: str = "public"
    NACOS_GROUP: str = "DEFAULT_GROUP"
    NACOS_CONFIG_DATA_ID: str = "gateway-config.json"
    NACOS_CONFIG_REFRESH_SEC: int = 5

    SERVICE_NAME: str = "gateway-service"
    SERVICE_IP: str = "gateway"
    SERVICE_PORT: int = 8080

    FRONTEND_UPSTREAM: str = "http://frontend:80"
    DISCOVERY_CACHE_TTL_SEC: int = 3

    RATE_LIMIT_RPS: float = 80.0
    RATE_LIMIT_BURST: int = 40
    CIRCUIT_FAIL_THRESHOLD: int = 5
    CIRCUIT_OPEN_SECONDS: int = 15
    CONNECT_TIMEOUT_SEC: float = 1.0
    READ_TIMEOUT_SEC: float = 3.0

    STATIC_SERVICE_FALLBACK_JSON: str = (
        '{"user-service":[["user-service-1",8001],["user-service-2",8001]],'
        '"goods-service":[["goods-service-1",8002],["goods-service-2",8002]],'
        '"order-service":[["order-service-1",8003],["order-service-2",8003]],'
        '"inventory-service":[["inventory-service-1",8004],["inventory-service-2",8004]]}'
    )

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def static_service_fallback(self) -> dict[str, list[tuple[str, int]]]:
        raw = json.loads(self.STATIC_SERVICE_FALLBACK_JSON)
        result: dict[str, list[tuple[str, int]]] = {}
        for service_name, items in raw.items():
            result[service_name] = [(str(host), int(port)) for host, port in items]
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
