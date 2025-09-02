# app/core/settings.py
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === App ===
    APP_NAME: str = "Sistema de Conciliación Bancaria"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # === DB (acepta DB_* y tus actuales DB_MSQL_*) ===
    # Valores “estándar”
    DB_HOST: str | None = Field(default=None)
    DB_PORT: int = Field(default=16751)  # <-- tu puerto por defecto
    DB_NAME: str | None = Field(default=None)
    DB_USER: str | None = Field(default=None)
    DB_PASSWORD: SecretStr = Field(default=SecretStr(""))

    # Aliases alternativos (los de tu .env actual)
    _DB_HOST_ALT: str | None = Field(default=None, alias="DB_MSQL_HOST")
    _DB_PORT_ALT: int | None = Field(default=None, alias="DB_MSQL_PORT")
    _DB_NAME_ALT: str | None = Field(default=None, alias="DB_MSQL_DATABASE")
    _DB_USER_ALT: str | None = Field(default=None, alias="DB_MSQL_USERNAME")
    _DB_PASS_ALT: str | None = Field(default=None, alias="DB_MSQL_PASSWORD")

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

    # Pydantic Settings v2
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
        host = self.DB_HOST or self._DB_HOST_ALT or ""
        port = int(self.DB_PORT or self._DB_PORT_ALT or 16751)
        name = self.DB_NAME or self._DB_NAME_ALT or ""
        user = self.DB_USER or self._DB_USER_ALT or ""
        pwd = self.DB_PASSWORD.get_secret_value() or (self._DB_PASS_ALT or "")
        return f"mysql+pymysql://{user}:{quote_plus(pwd)}@{host}:{port}/{name}"


settings = Settings()

# Crea carpeta de subidas si no existe
Path(settings.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
