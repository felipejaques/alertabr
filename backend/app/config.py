from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Configurações da aplicação via variáveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "AlertaBR API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://alertabr:alertabr@db:5432/alertabr"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # INMET
    INMET_BASE_URL: str = "https://apitempo.inmet.gov.br"

    # IBGE
    IBGE_BASE_URL: str = "https://servicodados.ibge.gov.br"

    # ANA (Agência Nacional de Águas)
    ANA_TELEMETRIA_URL: str = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx"
    ANA_INGEST_INTERVAL_HOURS: int = 2


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
