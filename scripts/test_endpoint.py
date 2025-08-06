#!/usr/bin/env python3
"""
Prueba el endpoint actualizado con el PDFProcessor mejorado
"""
import requests
import json
import os

def test_endpoint():
    """Prueba el endpoint /procesar-estado-cuenta"""
    url = "http://localhost:8000/api/v1/conciliacion/procesar-estado-cuenta"
    
    # Verificar si el archivo de prueba existe
    pdf_file = "test_real_format.pdf"
    if not os.path.exists(pdf_file):
        print(f"❌ Archivo de prueba no encontrado: {pdf_file}")
        return
    
    print(f"🧪 Probando endpoint con archivo: {pdf_file}")
    
    try:
        # Subir archivo
        with open(pdf_file, 'rb') as f:
            files = {'file': (pdf_file, f, 'application/pdf')}
            
            print("📤 Enviando archivo al servidor...")
            response = requests.post(url, files=files)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            print("✅ Respuesta exitosa:")
            print(f"   Banco detectado: {resultado.get('banco_detectado', 'N/A')}")
            print(f"   Total movimientos: {resultado.get('total_movimientos', 0)}")
            print(f"   Tiempo procesamiento: {resultado.get('tiempo_procesamiento', 0)}s")
            
            # Mostrar movimientos
            movimientos = resultado.get('movimientos', [])
            if movimientos:
                print(f"\n📋 Movimientos extraídos ({len(movimientos)}):")
                for i, mov in enumerate(movimientos[:5], 1):  # Mostrar solo los primeros 5
                    print(f"   {i}. {mov.get('fecha', 'N/A')} - {mov.get('concepto', 'N/A')} - ${mov.get('monto', 'N/A')} ({mov.get('tipo', 'N/A')})")
                if len(movimientos) > 5:
                    print(f"   ... y {len(movimientos) - 5} movimientos más")
            else:
                print("❌ No se extrajeron movimientos")
            
            # Mostrar estadísticas
            stats = resultado.get('estadisticas', {})
            if stats:
                print(f"\n📊 Estadísticas:")
                print(f"   Movimientos extraídos: {stats.get('movimientos_extraidos', 0)}")
                print(f"   Movimientos validados: {stats.get('movimientos_validados', 0)}")
                print(f"   Movimientos únicos: {stats.get('movimientos_unicos', 0)}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en la prueba: {str(e)}")

if __name__ == "__main__":
    test_endpoint() 