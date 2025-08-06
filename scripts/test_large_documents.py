#!/usr/bin/env python3
"""
Script para probar el procesamiento mejorado de documentos grandes (80+ páginas)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.gemini_processor import GeminiProcessor
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import fitz  # PyMuPDF

def crear_pdf_grande_simulado():
    """Crea un PDF grande simulado para probar el procesamiento por chunks."""
    filename = "test_large_document.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Crear 80 páginas con movimientos
    for pagina in range(80):
        # Encabezado de página
        c.drawString(50, height - 50, f"ESTADO DE CUENTA - PÁGINA {pagina + 1}")
        c.drawString(50, height - 70, "FECHA | REFERENCIA | CONCEPTO | MONTO | SALDO")
        
        # Movimientos de ejemplo para esta página
        movimientos_pagina = [
            (f"MAY.{pagina+1:02d}", f"REF{pagina+1:04d}001", "DEPOSITO EFECTIVO", "1,000.00", f"{1000 + pagina*100}.00"),
            (f"MAY.{pagina+1:02d}", f"REF{pagina+1:04d}002", "RETIRO CAJERO", "500.00", f"{500 + pagina*100}.00"),
            (f"MAY.{pagina+1:02d}", f"REF{pagina+1:04d}003", "COMISION MANEJO", "50.00", f"{450 + pagina*100}.00"),
            (f"MAY.{pagina+1:02d}", f"REF{pagina+1:04d}004", "INTERESES GANADOS", "25.00", f"{475 + pagina*100}.00"),
            (f"MAY.{pagina+1:02d}", f"REF{pagina+1:04d}005", "PAGO SERVICIOS", "200.00", f"{275 + pagina*100}.00")
        ]
        
        y = height - 100
        for fecha, ref, concepto, monto, saldo in movimientos_pagina:
            c.drawString(50, y, fecha)
            c.drawString(150, y, ref)
            c.drawString(250, y, concepto)
            c.drawString(400, y, monto)
            c.drawString(500, y, saldo)
            y -= 20
        
        c.showPage()
    
    c.save()
    return filename

def probar_documento_grande():
    """Prueba el procesamiento de documentos grandes."""
    processor = GeminiProcessor()
    
    print("🧪 PROBANDO PROCESAMIENTO DE DOCUMENTOS GRANDES")
    print("=" * 60)
    
    # Crear PDF grande
    pdf_grande = crear_pdf_grande_simulado()
    
    # Verificar número de páginas
    doc = fitz.open(pdf_grande)
    num_paginas = len(doc)
    doc.close()
    
    print(f"📄 PDF creado con {num_paginas} páginas")
    
    # Procesar
    resultado = processor.procesar_pdf(pdf_grande)
    
    print(f"\n📊 RESULTADOS:")
    print(f"✅ Éxito: {resultado.get('exito')}")
    print(f"🏦 Banco detectado: {resultado.get('banco_detectado')}")
    print(f"📊 Movimientos extraídos: {len(resultado.get('movimientos', []))}")
    print(f"🤖 Modelo utilizado: {resultado.get('modelo_utilizado')}")
    print(f"⏱️ Tiempo total: {resultado.get('tiempo_procesamiento_segundos', 0):.2f}s")
    
    # Mostrar algunos movimientos
    movimientos = resultado.get('movimientos', [])
    if movimientos:
        print(f"\n📋 Primeros 5 movimientos:")
        for i, mov in enumerate(movimientos[:5]):
            print(f"  {i+1}. {mov.get('fecha')} - {mov.get('concepto')[:30]}... - ${mov.get('monto')}")
        
        print(f"\n📋 Últimos 5 movimientos:")
        for i, mov in enumerate(movimientos[-5:]):
            print(f"  {len(movimientos)-4+i}. {mov.get('fecha')} - {mov.get('concepto')[:30]}... - ${mov.get('monto')}")
    
    # Limpiar archivo temporal
    if os.path.exists(pdf_grande):
        os.remove(pdf_grande)
    
    print(f"\n✅ Prueba completada! Se detectaron {len(movimientos)} movimientos de {num_paginas} páginas")

def probar_modelo_seleccion():
    """Prueba la selección de modelos según el número de páginas."""
    processor = GeminiProcessor()
    
    print("\n🤖 PROBANDO SELECCIÓN DE MODELOS")
    print("=" * 40)
    
    # Probar diferentes tamaños
    tamanos = [10, 25, 40, 60, 100]
    
    for tamano in tamanos:
        modelo = processor._determinar_modelo_por_paginas(tamano)
        print(f"📄 {tamano:3d} páginas → Modelo: {modelo}")
    
    print("\n📊 RESUMEN DE SELECCIÓN:")
    print("• < 20 páginas  → gemini-2.5-flash-lite")
    print("• 20-39 páginas → gemini-2.5-flash")
    print("• 40-79 páginas → gemini-2.5-pro")
    print("• 80+ páginas   → gemini-2.5-flash-exp")
    
    print("\n✅ Prueba de selección de modelos completada!")

if __name__ == "__main__":
    probar_modelo_seleccion()
    probar_documento_grande() 