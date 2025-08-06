import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Información de la aplicación
    APP_NAME: str = "Sistema de Conciliación Bancaria"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Configuración MySQL
    DB_MSQL_USERNAME: str = "root"
    DB_MSQL_PASSWORD: str = "NuevaPassword123!"
    DB_MSQL_DATABASE: str = "alertadefinitivo"
    DB_MSQL_HOST: str = "localhost"
    DB_MSQL_PORT: int = 3306
    DB_MSQL_DIALECT: str = "mysql"
    
    # Base de datos (construir URL desde variables MySQL)
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_MSQL_USERNAME}:{self.DB_MSQL_PASSWORD}@{self.DB_MSQL_HOST}:{self.DB_MSQL_PORT}/{self.DB_MSQL_DATABASE}?charset=utf8mb4"
    
    # Mantener variables legacy para compatibilidad
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "alertadefinitivo"
    DB_USER: str = "root"
    DB_PASSWORD: str = "NuevaPassword123!"
    
    # OpenAI API Key para OCR (requerida para conciliación)
    OPENAI_API_KEY: str = ""
    #agrega desde mi env 
    # Gemini API Key para procesamiento de PDFs
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    
    # Seguridad
    SECRET_KEY: str = "your-secret-key-here"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Configuración de logs
    LOG_LEVEL: str = "INFO"
    
    # Configuración de archivos para PDFs bancarios
    MAX_FILE_SIZE: int = 52428800  # 50MB para PDFs bancarios
    UPLOAD_FOLDER: str = "uploads/"
    ALLOWED_EXTENSIONS: str = "pdf"  # Solo PDFs para conciliación
    
    # Configuración específica de conciliación
    CONCILIACION_TOLERANCIA_MONTO: float = 1.00
    CONCILIACION_DIAS_TOLERANCIA: int = 3
    CONCILIACION_MAX_FILE_SIZE: int = 52428800  # 50MB
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Permitir campos extra para compatibilidad

# Instancia global de configuración
settings = Settings()

# Crear carpeta de uploads si no existe
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True) 