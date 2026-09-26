"""
Configuración centralizada de la aplicación.

Todos los valores se leen de variables de entorno (o de un archivo .env en
desarrollo local) usando pydantic-settings. Nada de configuración sensible
queda hardcodeada en el código: en Azure esto se resuelve inyectando las
variables desde Azure Key Vault / App Service Configuration, tal como indica
la Guía de Instalación y Despliegue.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Aplicación ---
    app_name: str = "AgeCare API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"  # development | staging | production
    debug: bool = True

    # --- Base de datos ---
    # Formato async de SQLAlchemy: postgresql+asyncpg://user:pass@host:port/db
    database_url: str = "postgresql+asyncpg://agecare:agecare@localhost:5432/agecare"
    db_echo: bool = False  # True para loguear cada SQL emitido (debug local)

    # --- Seguridad / JWT ---
    # HS256 para el MVP (ver sección 2.2 de la Especificación de Endpoints).
    # En producción este secreto DEBE venir de Azure Key Vault, nunca de un
    # valor por defecto en el código. Se usa un placeholder de 40+ caracteres
    # a propósito: HS256 recomienda una clave de al menos 32 bytes (RFC 7518
    # 3.2); un secreto corto genera un InsecureKeyLengthWarning de PyJWT.
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION_use_a_random_64_char_secret_value"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # --- CORS (web app / web admin futuras) ---
    cors_origins: list[str] = ["*"]  # ajustar en producción a dominios reales


@lru_cache
def get_settings() -> Settings:
    """Settings como singleton cacheado (evita releer el entorno en cada request)."""
    return Settings()
