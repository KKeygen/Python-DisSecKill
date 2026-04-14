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
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    INVENTORY_SERVICE_URL: str = "http://inventory-service-1:8004"
    GOODS_SERVICE_URL: str = "http://goods-service-1:8002"
    NACOS_ENABLED: bool = False
    NACOS_SERVER_ADDR: str = "nacos:8848"
    NACOS_NAMESPACE: str = "public"
    NACOS_GROUP: str = "DEFAULT_GROUP"
    SERVICE_NAME: str = "order-service"
    SERVICE_IP: str = "order-service-1"
    SERVICE_PORT: int = 8003

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://root:{self.MYSQL_ROOT_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def shard_url_template(self) -> str:
        """分片库URL模板，用于分库分表连接"""
        return (
            f"mysql+aiomysql://root:{self.MYSQL_ROOT_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{{db_name}}"
            f"?charset=utf8mb4"
        )

    @property
    def kafka_url(self) -> str:
        return f"{self.KAFKA_HOST}:{self.KAFKA_PORT}"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
