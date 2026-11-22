"""Configuration, read only from environment variables."""

from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ON_", frozen=True)

    environment: str = "local"
    version: str = "dev"
    log_level: str = "INFO"

    database_host: str
    database_port: int = 5432
    database_name: str
    database_user: str
    database_password: SecretStr

    api_port: int = 8000
    worker_metrics_port: int = 9100
    worker_poll_seconds: float = 2.0

    @property
    def database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.database_user,
                password=self.database_password.get_secret_value(),
                host=self.database_host,
                port=self.database_port,
                path=self.database_name,
            )
        )
