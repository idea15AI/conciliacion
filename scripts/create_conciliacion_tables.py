#!/usr/bin/env python3
"""
Script de migración para crear las tablas del módulo de conciliación bancaria

Este script crea todas las tablas necesarias para el módulo de conciliación
y actualiza los modelos existentes con las nuevas relaciones.
"""

import os
import sys
import logging
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, inspect
from app.core.database import engine, SessionLocal, Base
from app.core.config import settings

# Importar todos los modelos para que SQLAlchemy los registre
from app.models.mysql_models import *
from app.conciliacion.models import *

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verificar_conexion_db():
    """Verifica la conexión a la base de datos"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión a base de datos establecida")
            return True
    except Exception as e:
        logger.error(f"❌ Error conectando a la base de datos: {e}")
        return False


def obtener_tablas_existentes():
    """Obtiene lista de tablas existentes"""
    inspector = inspect(engine)
    return inspector.get_table_names()


def crear_tablas_conciliacion():
    """Crea las nuevas tablas del módulo de conciliación"""
    try:
        logger.info("🔧 Creando tablas del módulo de conciliación...")
        
        # Lista de tablas que vamos a crear
        tablas_conciliacion = [
            'movimientos_bancarios',
            'archivos_bancarios', 
            'resultados_conciliacion'
        ]
        
        # Verificar tablas existentes
        tablas_existentes = obtener_tablas_existentes()
        logger.info(f"📋 Tablas existentes: {len(tablas_existentes)}")
        
        # Crear solo las tablas nuevas
        tablas_a_crear = []
        for tabla in tablas_conciliacion:
            if tabla not in tablas_existentes:
                tablas_a_crear.append(tabla)
                logger.info(f"➕ Tabla a crear: {tabla}")
            else:
                logger.info(f"⚠️  Tabla ya existe: {tabla}")
        
        if tablas_a_crear:
            # Crear todas las tablas definidas en los modelos
            Base.metadata.create_all(bind=engine, checkfirst=True)
            logger.info(f"✅ Creadas {len(tablas_a_crear)} tablas nuevas")
        else:
            logger.info("ℹ️  Todas las tablas ya existen")
        
        # Verificar creación
        tablas_finales = obtener_tablas_existentes()
        for tabla in tablas_conciliacion:
            if tabla in tablas_finales:
                logger.info(f"✓ Confirmado: tabla {tabla} existe")
            else:
                logger.error(f"✗ Error: tabla {tabla} no fue creada")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        return False


def agregar_indices_optimizacion():
    """Agrega índices adicionales para optimización"""
    try:
        logger.info("🚀 Agregando índices de optimización...")
        
        indices_sql = [
            # Índices para movimientos_bancarios
            """
            CREATE INDEX IF NOT EXISTS idx_movimientos_empresa_fecha_estado 
            ON movimientos_bancarios(empresa_id, fecha DESC, estado)
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_movimientos_monto_tipo 
            ON movimientos_bancarios(monto, tipo)
            """,
            
            # Índices para archivos_bancarios
            """
            CREATE INDEX IF NOT EXISTS idx_archivos_empresa_periodo 
            ON archivos_bancarios(empresa_id, periodo_inicio, periodo_fin)
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_archivos_banco_fecha 
            ON archivos_bancarios(banco, fecha_procesamiento DESC)
            """,
            
            # Índices para resultados_conciliacion
            """
            CREATE INDEX IF NOT EXISTS idx_resultados_empresa_periodo 
            ON resultados_conciliacion(empresa_id, periodo_inicio, periodo_fin)
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_resultados_fecha_proceso 
            ON resultados_conciliacion(fecha_proceso DESC)
            """
        ]
        
        with engine.connect() as conn:
            for sql in indices_sql:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    logger.info("✓ Índice creado exitosamente")
                except Exception as e:
                    logger.warning(f"⚠️  Error creando índice: {e}")
        
        logger.info("✅ Índices de optimización procesados")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error agregando índices: {e}")
        return False


def verificar_integridad():
    """Verifica la integridad de las tablas creadas"""
    try:
        logger.info("🔍 Verificando integridad de las tablas...")
        
        with SessionLocal() as db:
            # Verificar que podemos hacer consultas básicas
            tests = [
                ("MovimientoBancario", "SELECT COUNT(*) FROM movimientos_bancarios"),
                ("ArchivoBancario", "SELECT COUNT(*) FROM archivos_bancarios"),
                ("ResultadoConciliacion", "SELECT COUNT(*) FROM resultados_conciliacion")
            ]
            
            for nombre, query in tests:
                try:
                    result = db.execute(text(query))
                    count = result.scalar()
                    logger.info(f"✓ {nombre}: {count} registros")
                except Exception as e:
                    logger.error(f"✗ Error en {nombre}: {e}")
                    return False
        
        logger.info("✅ Verificación de integridad completada")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en verificación: {e}")
        return False


def mostrar_resumen():
    """Muestra resumen del estado de las tablas"""
    try:
        logger.info("📊 Resumen del estado de la base de datos:")
        
        tablas_existentes = obtener_tablas_existentes()
        tablas_conciliacion = [
            'movimientos_bancarios',
            'archivos_bancarios', 
            'resultados_conciliacion'
        ]
        
        logger.info(f"📋 Total de tablas en la BD: {len(tablas_existentes)}")
        logger.info("🏦 Tablas del módulo de conciliación:")
        
        for tabla in tablas_conciliacion:
            estado = "✅ EXISTE" if tabla in tablas_existentes else "❌ FALTA"
            logger.info(f"   - {tabla}: {estado}")
        
        # Información adicional
        logger.info("\n🔗 Próximos pasos:")
        logger.info("   1. Instalar dependencias: uv add PyMuPDF pillow openai")
        logger.info("   2. Configurar OPENAI_API_KEY en .env")
        logger.info("   3. Probar endpoints en /docs")
        logger.info("   4. Revisar logs en tiempo real")
        
    except Exception as e:
        logger.error(f"❌ Error mostrando resumen: {e}")


def main():
    """Función principal del script de migración"""
    logger.info("🚀 Iniciando migración del módulo de conciliación bancaria")
    logger.info(f"🗄️  Base de datos: {settings.DATABASE_URL.split('@')[-1]}")  # Sin credenciales
    logger.info(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Paso 1: Verificar conexión
    if not verificar_conexion_db():
        logger.error("💥 No se pudo establecer conexión. Abortando.")
        sys.exit(1)
    
    # Paso 2: Crear tablas
    if not crear_tablas_conciliacion():
        logger.error("💥 Error creando tablas. Abortando.")
        sys.exit(1)
    
    # Paso 3: Agregar índices
    if not agregar_indices_optimizacion():
        logger.warning("⚠️  Error agregando índices, pero continuando...")
    
    # Paso 4: Verificar integridad
    if not verificar_integridad():
        logger.error("💥 Error en verificación de integridad. Revisar.")
        sys.exit(1)
    
    # Paso 5: Mostrar resumen
    mostrar_resumen()
    
    logger.info("🎉 ¡Migración completada exitosamente!")
    logger.info("🔗 El módulo de conciliación bancaria está listo para usar")


if __name__ == "__main__":
    main() 