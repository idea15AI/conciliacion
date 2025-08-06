#!/usr/bin/env python3
"""
Script para ejecutar el servidor de conciliación bancaria
"""

import sys
import os
import subprocess
import time

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_dependencies():
    """Verificar que todas las dependencias estén instaladas"""
    required_packages = [
        'fastapi',
        'uvicorn', 
        'sqlalchemy',
        'pymysql',
        'pydantic-settings',
        'python-multipart',
        'PyMuPDF',
        'pillow',
        'openai'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Faltan dependencias: {', '.join(missing_packages)}")
        print("Instala con: python3 -m pip install " + " ".join(missing_packages))
        return False
    
    print("✅ Todas las dependencias están instaladas")
    return True

def run_server():
    """Ejecutar el servidor"""
    print("🚀 Iniciando servidor de conciliación bancaria...")
    print("📋 Información:")
    print("   - URL: http://localhost:8000")
    print("   - Documentación: http://localhost:8000/docs")
    print("   - Health check: http://localhost:8000/health")
    print("   - Frontend: http://localhost:3000")
    print()
    print("⏹️  Presiona Ctrl+C para detener")
    print("=" * 50)
    
    try:
        # Ejecutar uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.core.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")
    except Exception as e:
        print(f"❌ Error ejecutando servidor: {e}")

def main():
    """Función principal"""
    print("🔍 Verificando dependencias...")
    
    if not check_dependencies():
        sys.exit(1)
    
    print()
    run_server()

if __name__ == "__main__":
    main() 