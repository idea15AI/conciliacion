#!/usr/bin/env python3
"""
Script para instalar y configurar la librería de Google Gemini
"""

import subprocess
import sys
import os

def instalar_gemini():
    """Instala la librería de Google Gemini."""
    print("🔧 Instalando Google Gemini...")
    
    try:
        # Instalar la librería oficial de Google
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "google-genai"
        ])
        print("✅ Google Gemini instalado correctamente")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando Google Gemini: {e}")
        return False
    
    return True

def verificar_instalacion():
    """Verifica que la instalación fue exitosa."""
    try:
        import google.genai as genai
        print("✅ Verificación exitosa: google.genai importado correctamente")
        return True
    except ImportError as e:
        print(f"❌ Error importando google.genai: {e}")
        return False

def configurar_api_key():
    """Guía para configurar la API key de Gemini."""
    print("\n🔑 CONFIGURACIÓN DE API KEY")
    print("=" * 50)
    print("Para usar Gemini, necesitas configurar tu API key:")
    print()
    print("1. Ve a: https://aistudio.google.com/app/apikey")
    print("2. Crea una nueva API key")
    print("3. Configura la variable de entorno:")
    print()
    print("   export GEMINI_API_KEY='tu-api-key-aqui'")
    print()
    print("O agrega al archivo .env:")
    print("   GEMINI_API_KEY=tu-api-key-aqui")
    print()
    print("4. Reinicia tu terminal o ejecuta: source .env")
    print()

def crear_archivo_config():
    """Crea un archivo de configuración de ejemplo."""
    config_content = """# Configuración de Gemini
# Reemplaza con tu API key real
GEMINI_API_KEY=tu-api-key-aqui

# Configuración adicional (opcional)
GEMINI_MODEL=gemini-2.0-flash
"""
    
    try:
        with open('.env.gemini', 'w') as f:
            f.write(config_content)
        print("📝 Archivo .env.gemini creado como ejemplo")
        print("   Edita este archivo con tu API key real")
    except Exception as e:
        print(f"⚠️ No se pudo crear .env.gemini: {e}")

def main():
    """Función principal."""
    print("🚀 Configurando Google Gemini para Conciliación")
    print("=" * 50)
    
    # Instalar librería
    if not instalar_gemini():
        return
    
    # Verificar instalación
    if not verificar_instalacion():
        return
    
    # Configurar API key
    configurar_api_key()
    
    # Crear archivo de configuración
    crear_archivo_config()
    
    print("\n✅ Configuración completada!")
    print("\n📋 Próximos pasos:")
    print("1. Configura tu API key de Gemini")
    print("2. Prueba el endpoint: /conciliacion/subir-estado-cuenta-gemini")
    print("3. Usa el HTML para subir archivos y ver resultados")
    print()
    print("🔗 Documentación: https://ai.google.dev/docs")

if __name__ == "__main__":
    main() 