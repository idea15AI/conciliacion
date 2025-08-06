#!/usr/bin/env python3
"""
Script para probar la selección automática de modelo basada en el número de páginas
"""

import os
import sys
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.gemini_processor import GeminiProcessor

def crear_pdf_simple(nombre_archivo: str, num_paginas: int = 1):
    """Crea un PDF simple con el número especificado de páginas"""
    c = canvas.Canvas(nombre_archivo, pagesize=letter)
    
    for i in range(num_paginas):
        c.drawString(100, 750, f"Página {i+1} de {num_paginas}")
        c.drawString(100, 700, "DETALLE DE TRANSACCIONES REALIZADAS")
        c.drawString(100, 650, "FECHA | CONCEPTO | DISPOSICIONES | PAGOS")
        c.drawString(100, 600, "15/01/24 | PAGO DE INTERÉS | $0.00 | $25,187.50")
        c.drawString(100, 550, "15/01/24 | PAGO DE CAPITAL | $0.00 | $83,333.33")
        
        if i < num_paginas - 1:
            c.showPage()
    
    c.save()
    print(f"✅ PDF creado: {nombre_archivo} con {num_paginas} páginas")

def probar_seleccion_modelo():
    """Prueba la selección automática de modelo"""
    processor = GeminiProcessor()
    
    # Crear PDFs de prueba con diferentes números de páginas
    casos_prueba = [
        ("test_1_pagina.pdf", 1),    # Debería usar flash-lite
        ("test_3_paginas.pdf", 3),   # Debería usar flash-lite
        ("test_6_paginas.pdf", 6),   # Debería usar flash-lite
        ("test_10_paginas.pdf", 10), # Debería usar flash-lite
        ("test_15_paginas.pdf", 15), # Debería usar flash
    ]
    
    print("🧪 Probando selección automática de modelo...")
    print("=" * 60)
    
    for nombre_archivo, num_paginas in casos_prueba:
        try:
            # Crear PDF de prueba
            crear_pdf_simple(nombre_archivo, num_paginas)
            
            # Probar selección de modelo
            modelo_seleccionado = processor._determinar_modelo_por_paginas(nombre_archivo)
            
            print(f"📄 {nombre_archivo} ({num_paginas} páginas)")
            print(f"   Modelo seleccionado: {modelo_seleccionado}")
            
            # Verificar que la selección es correcta
            if num_paginas <= 10 and "lite" in modelo_seleccionado:
                print("   ✅ CORRECTO: flash-lite para documento pequeño")
            elif num_paginas > 10 and "lite" not in modelo_seleccionado:
                print("   ✅ CORRECTO: flash para documento grande")
            else:
                print("   ❌ INCORRECTO: selección de modelo inesperada")
            
            print()
            
        except Exception as e:
            print(f"❌ Error probando {nombre_archivo}: {e}")
        finally:
            # Limpiar archivo de prueba
            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)

def probar_procesamiento_completo():
    """Prueba el procesamiento completo con diferentes tamaños de PDF"""
    processor = GeminiProcessor()
    
    print("\n🚀 Probando procesamiento completo...")
    print("=" * 60)
    
    # Crear PDF de prueba
    test_pdf = "test_procesamiento.pdf"
    crear_pdf_simple(test_pdf, 3)  # 3 páginas
    
    try:
        # Procesar PDF
        resultado = processor.procesar_pdf(test_pdf)
        
        print(f"📊 Resultados del procesamiento:")
        print(f"   Éxito: {resultado.get('exito', False)}")
        print(f"   Modelo utilizado: {resultado.get('modelo_utilizado', 'N/A')}")
        print(f"   Tiempo de procesamiento: {resultado.get('tiempo_procesamiento_segundos', 0)} segundos")
        print(f"   Banco detectado: {resultado.get('banco_detectado', 'N/A')}")
        print(f"   Total movimientos: {resultado.get('total_movimientos_extraidos', 0)}")
        
        if resultado.get('exito'):
            print("   ✅ Procesamiento exitoso")
        else:
            print(f"   ❌ Error: {resultado.get('mensaje', 'Error desconocido')}")
            
    except Exception as e:
        print(f"❌ Error en procesamiento completo: {e}")
    finally:
        # Limpiar archivo de prueba
        if os.path.exists(test_pdf):
            os.remove(test_pdf)

if __name__ == "__main__":
    print("🧪 TEST: Selección Automática de Modelo Gemini")
    print("=" * 60)
    
    # Verificar configuración
    try:
        processor = GeminiProcessor()
        print("✅ Configuración de Gemini correcta")
    except Exception as e:
        print(f"❌ Error de configuración: {e}")
        sys.exit(1)
    
    # Ejecutar pruebas
    probar_seleccion_modelo()
    probar_procesamiento_completo()
    
    print("\n🎉 Pruebas completadas!") 