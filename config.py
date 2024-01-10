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
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}/{self.postgres_db}"

    @property
    def alembic_conn_string(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}/{self.postgres_db}"


class RedisSettings(BaseSettings):
    redis_host: str
    redis_password: str
    redis_port: str = Field(default="6379")

    @property
    def conn_string(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"


class AuthConfig(BaseSettings):
    auth_uri: str
    secret_key: str
    cors_allow_origins: str

    @property
    def get_cors_origins(self) -> list:
        return self.cors_allow_origins.split(",")


class AppSettings(PostgresSettings, RedisSettings, AuthConfig):
    model_config = SettingsConfigDict(env_file=".env")


settings = AppSettings()
