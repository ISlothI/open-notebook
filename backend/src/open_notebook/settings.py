"""Configuration, read only from environment variables."""

from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProcessSettings(BaseSettings):
    """What every process needs, including those without a database."""

    model_config = SettingsConfigDict(env_prefix="ON_", frozen=True)

    environment: str = "local"
    version: str = "dev"
    log_level: str = "INFO"


class Settings(ProcessSettings):
    database_host: str
    database_port: int = 5432
    database_name: str
    database_user: str
    database_password: SecretStr

    api_port: int = 8000

    worker_metrics_port: int = 9100
    worker_poll_seconds: float = 2.0
    job_lease_seconds: float = 30.0

    embedder_url: str = "http://embedder:8001"

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
