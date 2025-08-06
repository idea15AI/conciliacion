#!/usr/bin/env python3
"""
Script para verificar la conexión a la base de datos MySQL
"""

import sys
import os
import logging
from datetime import datetime

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlalchemy import create_engine, text
    from app.core.config import settings
    from app.core.database import test_db_connection, init_db
except ImportError as e:
    print(f"❌ Error al importar módulos: {e}")
    print("Asegúrate de tener todas las dependencias instaladas:")
    print("python3 -m pip install sqlalchemy pymysql pydantic-settings")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_header():
    """Imprimir encabezado del script"""
    print("=" * 60)
    print("🔍 VERIFICADOR DE CONEXIÓN A BASE DE DATOS")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def print_config_info():
    """Mostrar información de configuración"""
    print("📋 CONFIGURACIÓN DE BASE DE DATOS:")
    print(f"   Host: {settings.DB_MSQL_HOST}")
    print(f"   Puerto: {settings.DB_MSQL_PORT}")
    print(f"   Base de datos: {settings.DB_MSQL_DATABASE}")
    print(f"   Usuario: {settings.DB_MSQL_USERNAME}")
    print(f"   Contraseña: {'*' * len(settings.DB_MSQL_PASSWORD)}")
    print(f"   URL: {settings.DATABASE_URL.replace(settings.DB_MSQL_PASSWORD, '*' * len(settings.DB_MSQL_PASSWORD))}")
    print()

def test_basic_connection():
    """Probar conexión básica a MySQL"""
    print("🔌 PROBANDO CONEXIÓN BÁSICA...")
    
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            connect_args={
                "charset": "utf8mb4",
                "use_unicode": True,
                "autocommit": True
            }
        )
        
        with engine.connect() as connection:
            # Probar consulta simple
            result = connection.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                print("✅ Conexión básica exitosa")
                return True
            else:
                print("❌ Conexión básica falló")
                return False
                
    except Exception as e:
        print(f"❌ Error en conexión básica: {e}")
        return False

def test_database_info():
    """Obtener información de la base de datos"""
    print("📊 INFORMACIÓN DE LA BASE DE DATOS...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as connection:
            # Información de la versión de MySQL
            result = connection.execute(text("SELECT VERSION() as version"))
            version = result.fetchone()[0]
            print(f"   Versión MySQL: {version}")
            
            # Información de la base de datos actual
            result = connection.execute(text("SELECT DATABASE() as current_db"))
            current_db = result.fetchone()[0]
            print(f"   Base de datos actual: {current_db}")
            
            # Tamaño de la base de datos
            result = connection.execute(text("""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size in MB'
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
            """))
            db_size = result.fetchone()[0]
            print(f"   Tamaño de la BD: {db_size} MB")
            
            # Número de tablas
            result = connection.execute(text("""
                SELECT COUNT(*) as table_count
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
            """))
            table_count = result.fetchone()[0]
            print(f"   Número de tablas: {table_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error al obtener información: {e}")
        return False

def test_schema_tables():
    """Verificar tablas del esquema de conciliación"""
    print("📋 VERIFICANDO TABLAS DEL ESQUEMA...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as connection:
            # Tablas principales del esquema
            main_tables = [
                'comprobantes_fiscales',
                'empresas_contribuyentes', 
                'conceptos_comprobantes'
            ]
            
            # Tablas de conversación
            chat_tables = [
                'conversaciones',
                'mensajes'
            ]
            
            print("   Tablas principales:")
            for table in main_tables:
                result = connection.execute(text(f"""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table}'
                """))
                exists = result.fetchone()[0] > 0
                status = "✅" if exists else "❌"
                print(f"     {status} {table}")
            
            print("   Tablas de conversación:")
            for table in chat_tables:
                result = connection.execute(text(f"""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table}'
                """))
                exists = result.fetchone()[0] > 0
                status = "✅" if exists else "❌"
                print(f"     {status} {table}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error al verificar tablas: {e}")
        return False

def test_table_data():
    """Verificar datos en las tablas principales"""
    print("📈 VERIFICANDO DATOS EN TABLAS...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as connection:
            tables_to_check = [
                'comprobantes_fiscales',
                'empresas_contribuyentes',
                'conceptos_comprobantes'
            ]
            
            for table in tables_to_check:
                try:
                    result = connection.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"   {table}: {count} registros")
                except Exception as e:
                    print(f"   ❌ Error en {table}: {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error al verificar datos: {e}")
        return False

def main():
    """Función principal del script"""
    print_header()
    print_config_info()
    
    # Probar conexión básica
    if not test_basic_connection():
        print("\n❌ NO SE PUDO ESTABLECER CONEXIÓN BÁSICA")
        print("Verifica:")
        print("   - Que MySQL esté ejecutándose")
        print("   - Que las credenciales sean correctas")
        print("   - Que la base de datos exista")
        sys.exit(1)
    
    print()
    
    # Obtener información de la base de datos
    test_database_info()
    print()
    
    # Verificar tablas del esquema
    test_schema_tables()
    print()
    
    # Verificar datos en tablas
    test_table_data()
    print()
    
    # Usar la función de test existente
    print("🔧 USANDO FUNCIÓN DE TEST EXISTENTE...")
    if test_db_connection():
        print("✅ Conexión verificada exitosamente")
    else:
        print("⚠️ Conexión verificada con advertencias")
    
    print()
    print("=" * 60)
    print("✅ VERIFICACIÓN COMPLETADA")
    print("=" * 60)

if __name__ == "__main__":
    main() 