from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    @property
    def postgres_conn_string(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def alembic_conn_string(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


class RedisSettings(BaseSettings):
    redis_host: str
    redis_password: str
    redis_port: str = Field(default="6379")

    @property
    def conn_string(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"


class RabbitMQSettings(BaseSettings):
    rabbitmq_default_user: str
    rabbitmq_default_pass: str
    rabbitmq_host: str
    rabbitmq_port: int

    @property
    def rabbitmq_conn_string(self) -> str:
        return f"amqp://{self.rabbitmq_default_user}:{self.rabbitmq_default_pass}@{self.rabbitmq_host}:{self.rabbitmq_port}"


class AuthConfig(BaseSettings):
    auth_uri: str
    secret_key: str
    cors_allow_origins: str

    @property
    def get_cors_origins(self) -> list:
        return self.cors_allow_origins.split(",")


class GrafanaConfig(BaseSettings):
    gf_security_admin_password: str


class AppSettings(PostgresSettings, RedisSettings, AuthConfig, RabbitMQSettings, GrafanaConfig):
    model_config = SettingsConfigDict(env_file=".env")


settings = AppSettings()
