#!/usr/bin/env python3
"""
Script para probar todas las rutas disponibles del sistema de conciliación bancaria
"""

import requests
import json
import sys
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def print_header():
    """Imprimir encabezado"""
    print("=" * 60)
    print("🧪 TESTER DE RUTAS - SISTEMA DE CONCILIACIÓN BANCARIA")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    print()

def test_endpoint(url, method="GET", data=None, description=""):
    """Probar un endpoint específico"""
    try:
        print(f"🔍 Probando: {description}")
        print(f"   URL: {url}")
        print(f"   Método: {method}")
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, json=data, timeout=10)
        
        if response.status_code == 200:
            print(f"   ✅ Status: {response.status_code}")
            try:
                result = response.json()
                if isinstance(result, dict) and len(result) > 0:
                    print(f"   📄 Respuesta: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}...")
                else:
                    print(f"   📄 Respuesta: {result}")
            except:
                print(f"   📄 Respuesta: {response.text[:100]}...")
        else:
            print(f"   ❌ Status: {response.status_code}")
            print(f"   📄 Error: {response.text[:200]}...")
        
        print()
        return response.status_code == 200
        
    except Exception as e:
        print(f"   💥 Error: {e}")
        print()
        return False

def test_basic_endpoints():
    """Probar endpoints básicos"""
    print("📋 PROBANDO ENDPOINTS BÁSICOS")
    print("-" * 40)
    
    endpoints = [
        ("/", "GET", None, "Endpoint raíz"),
        ("/health", "GET", None, "Health check"),
        ("/info", "GET", None, "Información de la aplicación"),
        ("/modules", "GET", None, "Información de módulos"),
        ("/docs", "GET", None, "Documentación Swagger"),
        ("/redoc", "GET", None, "Documentación ReDoc")
    ]
    
    success_count = 0
    for url, method, data, desc in endpoints:
        if test_endpoint(f"{BASE_URL}{url}", method, data, desc):
            success_count += 1
    
    print(f"✅ Endpoints básicos: {success_count}/{len(endpoints)} exitosos")
    print()

def test_conciliacion_endpoints():
    """Probar endpoints de conciliación"""
    print("🏦 PROBANDO ENDPOINTS DE CONCILIACIÓN")
    print("-" * 40)
    
    # Endpoints que no requieren parámetros específicos
    endpoints = [
        ("/conciliacion/empresas", "GET", None, "Listar empresas contribuyentes"),
    ]
    
    success_count = 0
    for url, method, data, desc in endpoints:
        if test_endpoint(f"{API_BASE}{url}", method, data, desc):
            success_count += 1
    
    print(f"✅ Endpoints de conciliación: {success_count}/{len(endpoints)} exitosos")
    print()

def test_specific_endpoints():
    """Probar endpoints que requieren parámetros específicos"""
    print("🎯 PROBANDO ENDPOINTS ESPECÍFICOS")
    print("-" * 40)
    
    # Obtener empresas primero para usar sus IDs
    try:
        response = requests.get(f"{API_BASE}/conciliacion/empresas", timeout=10)
        if response.status_code == 200:
            empresas = response.json()
            if empresas and len(empresas) > 0:
                empresa_id = empresas[0].get('id', 1)  # Usar la primera empresa
                
                endpoints = [
                    (f"/conciliacion/reporte/{empresa_id}", "GET", None, f"Reporte de conciliación (empresa {empresa_id})"),
                    (f"/conciliacion/movimientos/{empresa_id}", "GET", None, f"Movimientos bancarios (empresa {empresa_id})"),
                    (f"/conciliacion/archivos/{empresa_id}", "GET", None, f"Archivos bancarios (empresa {empresa_id})"),
                    (f"/conciliacion/estadisticas/{empresa_id}", "GET", None, f"Estadísticas (empresa {empresa_id})"),
                ]
                
                success_count = 0
                for url, method, data, desc in endpoints:
                    if test_endpoint(f"{API_BASE}{url}", method, data, desc):
                        success_count += 1
                
                print(f"✅ Endpoints específicos: {success_count}/{len(endpoints)} exitosos")
            else:
                print("⚠️ No hay empresas disponibles para probar endpoints específicos")
        else:
            print("❌ No se pudieron obtener empresas para probar endpoints específicos")
    except Exception as e:
        print(f"❌ Error obteniendo empresas: {e}")
    
    print()

def test_documentation():
    """Probar acceso a documentación"""
    print("📚 PROBANDO DOCUMENTACIÓN")
    print("-" * 40)
    
    docs_urls = [
        ("/docs", "Documentación Swagger UI"),
        ("/redoc", "Documentación ReDoc"),
        ("/openapi.json", "Especificación OpenAPI")
    ]
    
    success_count = 0
    for url, desc in docs_urls:
        try:
            response = requests.get(f"{BASE_URL}{url}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {desc}: Accesible")
                success_count += 1
            else:
                print(f"❌ {desc}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {desc}: Error - {e}")
    
    print(f"✅ Documentación: {success_count}/{len(docs_urls)} accesible")
    print()

def show_available_routes():
    """Mostrar todas las rutas disponibles"""
    print("🗺️ RUTAS DISPONIBLES")
    print("-" * 40)
    
    routes = {
        "Endpoints Básicos": {
            "GET /": "Información del sistema",
            "GET /health": "Estado de salud del sistema",
            "GET /info": "Información detallada",
            "GET /modules": "Información de módulos"
        },
        "Documentación": {
            "GET /docs": "Swagger UI",
            "GET /redoc": "ReDoc",
            "GET /openapi.json": "Especificación OpenAPI"
        },
        "API Conciliación": {
            "GET /api/v1/conciliacion/empresas": "Listar empresas contribuyentes",
            "POST /api/v1/conciliacion/subir-estado-cuenta": "Subir PDF bancario",
            "POST /api/v1/conciliacion/ejecutar": "Ejecutar conciliación",
            "GET /api/v1/conciliacion/reporte/{empresa_id}": "Obtener reporte",
            "GET /api/v1/conciliacion/movimientos/{empresa_id}": "Listar movimientos",
            "GET /api/v1/conciliacion/archivos/{empresa_id}": "Listar archivos",
            "GET /api/v1/conciliacion/estadisticas/{empresa_id}": "Estadísticas",
            "PATCH /api/v1/conciliacion/movimientos/{movimiento_id}": "Actualizar movimiento"
        }
    }
    
    for category, endpoints in routes.items():
        print(f"\n📂 {category}:")
        for route, description in endpoints.items():
            print(f"   {route}")
            print(f"      └─ {description}")
    
    print()

def main():
    """Función principal"""
    print_header()
    
    # Verificar que el servidor esté ejecutándose
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ El servidor no está ejecutándose correctamente")
            print("Ejecuta: python3 -m uvicorn app.core.main:app --reload --host 0.0.0.0 --port 8000")
            sys.exit(1)
    except Exception as e:
        print("❌ No se puede conectar al servidor")
        print("Asegúrate de que esté ejecutándose en http://localhost:8000")
        sys.exit(1)
    
    print("✅ Servidor conectado correctamente")
    print()
    
    # Mostrar rutas disponibles
    show_available_routes()
    
    # Probar endpoints
    test_basic_endpoints()
    test_conciliacion_endpoints()
    test_specific_endpoints()
    test_documentation()
    
    print("=" * 60)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 60)
    print("💡 Para más información visita:")
    print(f"   📖 Documentación: {BASE_URL}/docs")
    print(f"   🔧 Health Check: {BASE_URL}/health")
    print(f"   📊 Información: {BASE_URL}/info")

if __name__ == "__main__":
    main() 