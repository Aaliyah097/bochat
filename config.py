from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    redis_host: str
    redis_password: str
    redis_port: str = Field(default="6379")

    @property
    def conn_string(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"


class AuthConfig(BaseSettings):
    create_token_uri: str
    verify_token_uri: str
    secret_key: str
    cors_allow_origins: str

    @property
    def get_cors_origins(self) -> list:
        return self.cors_allow_origins.split(",")


class GrafanaConfig(BaseSettings):
    gf_security_admin_password: str


class MongoDBConfig(BaseSettings):
    mongo_initdb_root_username: str
    mongo_initdb_root_password: str
    mongo_initdb_database: str
    mongo_initdb_host: str
    mongo_initdb_port: int

    @property
    def mongodb_conn_string(self):
        return f"mongodb://{self.mongo_initdb_root_username}:{self.mongo_initdb_root_password}@{self.mongo_initdb_host}:{str(self.mongo_initdb_port)}/{self.mongo_initdb_database}"


class FireBaseSettings(BaseSettings):
    google_conf_path: str
    google_jwt_ttl: int = Field(default=3600)
    google_token_url: str
    firebase_send_address: str


class LokiSettings(BaseSettings):
    loki_host: str
    loki_port: int

    @property
    def loki_endpoint(self):
        return f"http://{self.loki_host}:{str(self.loki_port)}/loki/api/v1/push"


class AppSettings(RedisSettings,
                  AuthConfig,
                  GrafanaConfig,
                  MongoDBConfig,
                  FireBaseSettings,
                  LokiSettings):
    model_config = SettingsConfigDict(env_file=".env")


settings = AppSettings()
