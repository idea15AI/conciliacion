# app/core/database.py
from typing import Generator
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.settings import settings

# Configurar logging con el nivel normalizado
logging.basicConfig(level=settings.LOG_LEVEL_NUM)
logger = logging.getLogger(__name__)

# Crear engine de base de datos con configuraciones específicas de MySQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,            # pon True si quieres debug SQL
    pool_recycle=3600,     # reciclar conexiones cada hora
    connect_args={
        "charset": "utf8mb4",
        "use_unicode": True,
    },
)

# Crear SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Generador de sesiones de base de datos para dependency injection
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializar base de datos - verificar tablas esperadas
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME IN ('comprobantes_fiscales', 'empresas_contribuyentes', 'conceptos_comprobantes')
            """))
            tablas_principales = [row[0] for row in result.fetchall()]
            if len(tablas_principales) >= 3:
                logger.info("✅ Tablas principales del esquema disponibles")
            else:
                logger.warning("⚠️ Tablas principales no encontradas. Verificar migración.")

            result_chat = connection.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME IN ('conversaciones', 'mensajes')
            """))
            tablas_chat = [row[0] for row in result_chat.fetchall()]
            if len(tablas_chat) >= 2:
                logger.info("✅ Tablas de conversación disponibles")
            else:
                logger.warning("⚠️ Tablas de conversación no encontradas.")

        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"Error al verificar tablas: {e}")
        raise


def test_db_connection() -> bool:
    """
    Probar conexión a la base de datos MySQL y verificar tablas
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("Conexión a MySQL exitosa")

            tables_check = connection.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME IN ('comprobantes_fiscales', 'empresas_contribuyentes', 'conceptos_comprobantes')
            """))
            existing_tables = [row[0] for row in tables_check.fetchall()]
            logger.info(f"Tablas principales encontradas: {existing_tables}")

            if len(existing_tables) >= 3:
                logger.info("✅ Tablas principales del esquema están disponibles")
                return True

            logger.warning("⚠️ Algunas tablas principales no encontradas")
            return False

    except Exception as e:
        logger.error(f"Error de conexión a MySQL: {e}")
        return False
