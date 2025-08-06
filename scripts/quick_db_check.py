#!/usr/bin/env python3
"""
Script rápido para verificar conexión a la base de datos
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlalchemy import create_engine, text
    from app.core.config import settings
except ImportError as e:
    print(f"❌ Error: {e}")
    print("Instala las dependencias: python3 -m pip install sqlalchemy pymysql")
    sys.exit(1)

def quick_check():
    """Verificación rápida de conexión"""
    print("🔍 Verificando conexión a la base de datos...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as connection:
            # Probar conexión básica
            result = connection.execute(text("SELECT 1"))
            
            # Verificar que existe la base de datos
            result = connection.execute(text("SELECT DATABASE()"))
            db_name = result.fetchone()[0]
            
            # Contar tablas principales
            result = connection.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name IN ('comprobantes_fiscales', 'empresas_contribuyentes', 'conceptos_comprobantes')
            """))
            table_count = result.fetchone()[0]
            
            print(f"✅ Conexión exitosa a: {db_name}")
            print(f"📋 Tablas principales encontradas: {table_count}/3")
            
            if table_count >= 3:
                print("🎉 Base de datos lista para usar")
                return True
            else:
                print("⚠️ Faltan algunas tablas del esquema")
                return False
                
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    success = quick_check()
    sys.exit(0 if success else 1) 