from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "disseckill"
    MYSQL_ROOT_PASSWORD: str = "disseckill_root_2026"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    KAFKA_HOST: str = "localhost"
    KAFKA_PORT: int = 9092
    NACOS_ENABLED: bool = False
    NACOS_SERVER_ADDR: str = "nacos:8848"
    NACOS_NAMESPACE: str = "public"
    NACOS_GROUP: str = "DEFAULT_GROUP"
    NACOS_CONFIG_DATA_ID: str = "inventory-config.json"
    NACOS_CONFIG_REFRESH_SEC: int = 5
    SERVICE_NAME: str = "inventory-service"
    SERVICE_IP: str = "inventory-service-1"
    SERVICE_PORT: int = 8004
    SECKILL_DEFAULT_LIMIT_PER_USER: int = 1

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://root:{self.MYSQL_ROOT_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/2"

    @property
    def kafka_url(self) -> str:
        return f"{self.KAFKA_HOST}:{self.KAFKA_PORT}"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
