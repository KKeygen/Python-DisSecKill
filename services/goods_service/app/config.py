from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_SLAVE_HOST: str = "mysql-slave"
    MYSQL_SLAVE_PORT: int = 3306
    MYSQL_DATABASE: str = "disseckill"
    MYSQL_ROOT_PASSWORD: str = "disseckill_root_2026"
    NACOS_ENABLED: bool = False
    NACOS_SERVER_ADDR: str = "nacos:8848"
    NACOS_NAMESPACE: str = "public"
    NACOS_GROUP: str = "DEFAULT_GROUP"
    SERVICE_NAME: str = "goods-service"
    SERVICE_IP: str = "goods-service-1"
    SERVICE_PORT: int = 8002
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    ES_HOST: str = "elasticsearch"
    ES_PORT: int = 9200

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://root:{self.MYSQL_ROOT_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def database_url_read(self) -> str:
        return (
            f"mysql+aiomysql://root:{self.MYSQL_ROOT_PASSWORD}"
            f"@{self.MYSQL_SLAVE_HOST}:{self.MYSQL_SLAVE_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    @property
    def elasticsearch_url(self) -> str:
        return f"http://{self.ES_HOST}:{self.ES_PORT}"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


