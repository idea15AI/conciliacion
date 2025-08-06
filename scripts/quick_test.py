#!/usr/bin/env python3
"""
Script rápido para probar las funcionalidades principales del sistema
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def quick_test():
    """Prueba rápida de funcionalidades principales"""
    print("🚀 PRUEBA RÁPIDA - SISTEMA DE CONCILIACIÓN BANCARIA")
    print("=" * 50)
    
    # 1. Health Check
    print("1️⃣ Health Check:")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {data['status']}")
            print(f"   🗄️ DB: {'✅' if data['db_connection'] else '❌'}")
            print(f"   📅 Timestamp: {data['timestamp']}")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 2. Información del sistema
    print("2️⃣ Información del sistema:")
    try:
        response = requests.get(f"{BASE_URL}/info")
        if response.status_code == 200:
            data = response.json()
            print(f"   📱 App: {data['app_name']}")
            print(f"   🔢 Versión: {data['version']}")
            print(f"   🐛 Debug: {data['debug']}")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 3. Empresas disponibles
    print("3️⃣ Empresas disponibles:")
    try:
        response = requests.get(f"{API_BASE}/conciliacion/empresas")
        if response.status_code == 200:
            empresas = response.json()
            print(f"   📊 Total empresas: {len(empresas)}")
            for empresa in empresas:
                print(f"   🏢 {empresa['razon_social']} (ID: {empresa['id']})")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 4. Estadísticas de primera empresa
    print("4️⃣ Estadísticas (primera empresa):")
    try:
        response = requests.get(f"{API_BASE}/conciliacion/empresas")
        if response.status_code == 200:
            empresas = response.json()
            if empresas:
                empresa_id = empresas[0]['id']
                response = requests.get(f"{API_BASE}/conciliacion/estadisticas/{empresa_id}")
                if response.status_code == 200:
                    stats = response.json()
                    print(f"   🏢 Empresa: {stats['empresa']['razon_social']}")
                    print(f"   📊 Movimientos total: {stats['movimientos']['total']}")
                    print(f"   ✅ Conciliados: {stats['movimientos']['conciliados']}")
                    print(f"   ⏳ Pendientes: {stats['movimientos']['pendientes']}")
                else:
                    print(f"   ❌ Error estadísticas: {response.status_code}")
            else:
                print("   ⚠️ No hay empresas disponibles")
        else:
            print(f"   ❌ Error obteniendo empresas: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 5. URLs importantes
    print("5️⃣ URLs importantes:")
    print(f"   🌐 API Base: {BASE_URL}")
    print(f"   📖 Documentación: {BASE_URL}/docs")
    print(f"   🔧 Health Check: {BASE_URL}/health")
    print(f"   📊 Información: {BASE_URL}/info")
    print(f"   🏦 API Conciliación: {API_BASE}/conciliacion")
    
    print()
    print("=" * 50)
    print("✅ PRUEBA RÁPIDA COMPLETADA")
    print("💡 Para más detalles ejecuta: python3 scripts/test_routes.py")

if __name__ == "__main__":
    quick_test() 