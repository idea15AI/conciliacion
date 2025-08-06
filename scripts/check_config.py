#!/usr/bin/env python3
"""
Script para verificar la configuración del sistema
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_config():
    """Verifica la configuración del sistema."""
    
    print("🔧 Verificando configuración del sistema...")
    print("=" * 50)
    
    # Verificar archivo .env
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ Archivo .env encontrado: {env_file}")
        
        # Leer variables del archivo .env
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        # Buscar GEMINI_API_KEY
        if "GEMINI_API_KEY" in env_content:
            print("✅ GEMINI_API_KEY encontrada en .env")
            # Extraer el valor
            for line in env_content.split('\n'):
                if line.startswith('GEMINI_API_KEY='):
                    key_value = line.split('=')[1]
                    print(f"🔑 Valor: {key_value[:10]}...{key_value[-4:]}")
                    break
        else:
            print("❌ GEMINI_API_KEY no encontrada en .env")
    else:
        print(f"❌ Archivo .env no encontrado: {env_file}")
    
    print("\n📋 Verificando variables de entorno...")
    
    # Verificar variable de entorno
    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        print(f"✅ GEMINI_API_KEY en variables de entorno: {gemini_key[:10]}...{gemini_key[-4:]}")
    else:
        print("❌ GEMINI_API_KEY no encontrada en variables de entorno")
    
    print("\n📋 Verificando configuración desde settings...")
    
    try:
        from app.core.config import settings
        gemini_key_settings = settings.GEMINI_API_KEY
        if gemini_key_settings:
            print(f"✅ GEMINI_API_KEY en settings: {gemini_key_settings[:10]}...{gemini_key_settings[-4:]}")
        else:
            print("❌ GEMINI_API_KEY no encontrada en settings")
    except Exception as e:
        print(f"❌ Error cargando settings: {e}")
    
    print("\n📋 Verificando procesador Gemini...")
    
    try:
        from app.conciliacion.gemini_processor import GeminiProcessor
        processor = GeminiProcessor()
        print("✅ Procesador Gemini inicializado correctamente")
    except Exception as e:
        print(f"❌ Error inicializando procesador Gemini: {e}")
    
    print("\n🎉 Verificación completada!")

if __name__ == "__main__":
    check_config() 