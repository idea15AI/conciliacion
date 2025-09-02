# app/core/settings.py
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, AliasChoices, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === App ===
    APP_NAME: str = "Sistema de Conciliación Bancaria"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # === DB (acepta DB_* y DB_MSQL_*) ===
    DB_HOST: str = Field(validation_alias=AliasChoices("DB_HOST", "DB_MSQL_HOST"))
    DB_PORT: int = Field(default=16751, validation_alias=AliasChoices("DB_PORT", "DB_MSQL_PORT"))
    DB_NAME: str = Field(validation_alias=AliasChoices("DB_NAME", "DB_MSQL_DATABASE"))
    DB_USER: str = Field(validation_alias=AliasChoices("DB_USER", "DB_MSQL_USERNAME"))
    DB_PASSWORD: SecretStr = Field(validation_alias=AliasChoices("DB_PASSWORD", "DB_MSQL_PASSWORD"))

    # === APIs ===
    OPENAI_API_KEY: Optional[SecretStr] = None
    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # === Seguridad ===
    SECRET_KEY: SecretStr = SecretStr("change-me")  # define en entorno en prod

    # === CORS / Archivos ===
    CORS_ORIGINS: str = ""
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER: str = "uploads"
    ALLOWED_EXTENSIONS: str = "pdf"

    # Config de Pydantic Settings v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Normaliza ruta de uploads
    @field_validator("UPLOAD_FOLDER", mode="before")
    @classmethod
    def _normalize_upload_folder(cls, v: str) -> str:
        return v.rstrip("/")

    # Listas derivadas
    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS.strip():
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()]

    # URL de conexión (escapa la contraseña por seguridad)
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{quote_plus(self.DB_PASSWORD.get_secret_value())}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()

# Crea carpeta de subidas si no existe
Path(settings.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
