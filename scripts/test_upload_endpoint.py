#!/usr/bin/env python3
"""
Script para probar la ruta de subir estado de cuenta
"""

import requests
import json
import sys
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_upload_endpoint():
    """Probar el endpoint de subir estado de cuenta"""
    print("📤 PROBANDO ENDPOINT DE SUBIR ESTADO DE CUENTA")
    print("=" * 60)
    
    # 1. Obtener empresas disponibles
    print("1️⃣ Obteniendo empresas disponibles...")
    try:
        response = requests.get(f"{API_BASE}/conciliacion/empresas")
        if response.status_code == 200:
            empresas = response.json()
            print(f"   ✅ Empresas encontradas: {len(empresas)}")
            for empresa in empresas:
                print(f"   🏢 {empresa['razon_social']} (RFC: {empresa['rfc']})")
        else:
            print(f"   ❌ Error: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    print()
    
    # 2. Crear un archivo PDF de prueba
    print("2️⃣ Creando archivo PDF de prueba...")
    test_pdf_path = "test_estado_cuenta.pdf"
    
    # Crear un PDF simple de prueba (esto es solo para demostración)
    try:
        # Crear un PDF básico con contenido de prueba
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(test_pdf_path, pagesize=letter)
        c.drawString(100, 750, "ESTADO DE CUENTA BANCARIO")
        c.drawString(100, 730, "Banco: BANORTE")
        c.drawString(100, 710, "Cuenta: 1234-5678-9012-3456")
        c.drawString(100, 690, "Periodo: Enero 2024")
        c.drawString(100, 670, "Saldo Inicial: $10,000.00")
        c.drawString(100, 650, "Saldo Final: $12,500.00")
        c.drawString(100, 630, "")
        c.drawString(100, 610, "MOVIMIENTOS:")
        c.drawString(100, 590, "01/01/2024 - DEPOSITO - $2,000.00")
        c.drawString(100, 570, "05/01/2024 - RETIRO - $500.00")
        c.drawString(100, 550, "15/01/2024 - DEPOSITO - $1,000.00")
        c.save()
        
        print(f"   ✅ PDF de prueba creado: {test_pdf_path}")
    except ImportError:
        print("   ⚠️ reportlab no disponible, creando archivo de texto...")
        # Crear un archivo de texto como alternativa
        with open(test_pdf_path, 'w') as f:
            f.write("ESTADO DE CUENTA BANCARIO\n")
            f.write("Banco: BANORTE\n")
            f.write("Cuenta: 1234-5678-9012-3456\n")
            f.write("Periodo: Enero 2024\n")
            f.write("Saldo Inicial: $10,000.00\n")
            f.write("Saldo Final: $12,500.00\n")
        print(f"   ✅ Archivo de texto creado: {test_pdf_path}")
    except Exception as e:
        print(f"   ❌ Error creando archivo: {e}")
        return
    
    print()
    
    # 3. Probar el endpoint de subir archivo
    print("3️⃣ Probando endpoint de subir archivo...")
    
    if empresas:
        rfc_empresa = empresas[0]['rfc']  # Usar la primera empresa
        
        try:
            # Preparar los datos para el POST
            files = {
                'file': (test_pdf_path, open(test_pdf_path, 'rb'), 'application/pdf')
            }
            data = {
                'rfc_empresa': rfc_empresa
            }
            
            print(f"   📤 Enviando archivo para empresa: {rfc_empresa}")
            print(f"   📁 Archivo: {test_pdf_path}")
            
            response = requests.post(
                f"{API_BASE}/conciliacion/subir-estado-cuenta",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                resultado = response.json()
                print(f"   ✅ Éxito! Status: {response.status_code}")
                print(f"   📊 Resultado:")
                print(f"      - Éxito: {resultado.get('exito', False)}")
                print(f"      - Mensaje: {resultado.get('mensaje', 'N/A')}")
                print(f"      - Archivo ID: {resultado.get('archivo_id', 'N/A')}")
                print(f"      - Banco detectado: {resultado.get('banco_detectado', 'N/A')}")
                print(f"      - Movimientos extraídos: {resultado.get('total_movimientos_extraidos', 0)}")
                print(f"      - Tiempo procesamiento: {resultado.get('tiempo_procesamiento_segundos', 0)}s")
                
                if resultado.get('errores'):
                    print(f"      - Errores: {resultado['errores']}")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   📄 Respuesta: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ Error en la petición: {e}")
    
    print()
    
    # 4. Limpiar archivo de prueba
    print("4️⃣ Limpiando archivo de prueba...")
    try:
        os.remove(test_pdf_path)
        print(f"   ✅ Archivo eliminado: {test_pdf_path}")
    except Exception as e:
        print(f"   ⚠️ No se pudo eliminar archivo: {e}")
    
    print()
    print("=" * 60)
    print("✅ PRUEBA COMPLETADA")
    print("=" * 60)

def show_upload_info():
    """Mostrar información sobre el endpoint de subir archivo"""
    print("📋 INFORMACIÓN DEL ENDPOINT DE SUBIR ESTADO DE CUENTA")
    print("=" * 60)
    
    print("🔗 URL: POST /api/v1/conciliacion/subir-estado-cuenta")
    print()
    
    print("📝 Parámetros requeridos:")
    print("   - rfc_empresa: RFC de la empresa (string)")
    print("   - file: Archivo PDF del estado de cuenta (máximo 50MB)")
    print()
    
    print("📤 Ejemplo de uso con curl:")
    print("curl -X POST \\")
    print("  -F 'rfc_empresa=DMF9501184U9' \\")
    print("  -F 'file=@estado_cuenta.pdf' \\")
    print("  http://localhost:8000/api/v1/conciliacion/subir-estado-cuenta")
    print()
    
    print("📊 Respuesta esperada:")
    print("   - exito: boolean")
    print("   - mensaje: string")
    print("   - archivo_id: integer")
    print("   - banco_detectado: string")
    print("   - total_movimientos_extraidos: integer")
    print("   - tiempo_procesamiento_segundos: integer")
    print()
    
    print("💡 Para probar en el navegador:")
    print("   Visita: http://localhost:8000/docs")
    print("   Busca: POST /api/v1/conciliacion/subir-estado-cuenta")
    print("   Haz clic en 'Try it out'")

def main():
    """Función principal"""
    print("🔍 TESTER DE ENDPOINT DE SUBIR ESTADO DE CUENTA")
    print("=" * 60)
    
    # Verificar que el servidor esté ejecutándose
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ El servidor no está ejecutándose")
            print("Ejecuta: python3 -m uvicorn app.core.main:app --reload --host 0.0.0.0 --port 8000")
            sys.exit(1)
    except Exception as e:
        print("❌ No se puede conectar al servidor")
        print("Asegúrate de que esté ejecutándose en http://localhost:8000")
        sys.exit(1)
    
    print("✅ Servidor conectado correctamente")
    print()
    
    # Mostrar información
    show_upload_info()
    print()
    
    # Ejecutar prueba
    test_upload_endpoint()

if __name__ == "__main__":
    main() 