#!/usr/bin/env python3
"""
Script para probar INBURSA con el formato real que incluye conceptos multi-línea
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.gemini_processor import GeminiProcessor
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def crear_pdf_inbursa_real():
    """Crea un PDF de INBURSA con el formato real."""
    filename = "test_inbursa_real_format.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Encabezado
    c.drawString(50, height - 50, "INBURSA - ESTADO DE CUENTA")
    
    # Movimientos con formato real
    movimientos = [
        ("MAY. 26", "3438154784", "IVA TASA DE DESCTO CREDITO\nTasa IVA 16.0 %", "1.23", "62,087.21"),
        ("MAY. 26", "3438154788", "LIQUIDACION ADQUIRENTE DEBITO\nLIQUIDACION ADQ DEBITO-8993380", "3,725.00", "65,812.21"),
        ("MAY. 26", "3438154792", "TASA DE DESCTO DEBITO\nAPLICACION DE TASAS DE DESCUENTO-DEBITO-8993380", "79.72", "65,732.49"),
        ("MAY. 26", "3438154792", "IVA TASA DE DESCTO DEBITO\nTasa IVA 16.0 %", "12.76", "65,719.73"),
        ("MAY. 26", "3438280800", "LIQUIDACION ADQUIRENTE DEBITO\nLIQUIDACION ADQ DEBITO-8993380", "165.00", "65,884.73"),
        ("MAY. 27", "3440051070", "LIQUIDACION ADQUIRENTE DEBITO\nLIQUIDACION ADQ DEBITO-8993380", "1,115.00", "66,995.64"),
        ("MAY. 27", "3440302021", "DEPOSITO TEF\n1042404815627 OPERADORA PAYPAL DE MEXICO S DE RL\n106", "1,417.38", "68,385.34"),
        ("MAY. 28", "3441291368", "LIQUIDACION ADQUIRENTE CREDITO\nLIQUIDACION ADQ CREDITO-8993380", "665.00", "69,050.34"),
        ("MAY. 31", "3447637997", "INTERESES GANADOS", "309.08", "74,361.28"),
        ("MAY. 31", "3447637997", "COMISION MANEJO DE CUENTA", "200.00", "74,137.11"),
        ("MAY. 31", "3447637997", "IVA COMISION MANEJO DE CUENTA", "32.00", "74,105.11")
    ]
    
    y = height - 100
    for fecha, ref, concepto, monto, saldo in movimientos:
        # Fecha y referencia
        c.drawString(50, y, fecha)
        c.drawString(120, y, ref)
        
        # Concepto (puede ser múltiples líneas)
        lineas_concepto = concepto.split('\n')
        for i, linea in enumerate(lineas_concepto):
            c.drawString(200, y - (i * 15), linea)
        
        # Monto y saldo
        c.drawString(450, y, monto)
        c.drawString(520, y, saldo)
        
        y -= 40  # Más espacio para conceptos multi-línea
    
    c.save()
    return filename

def probar_inbursa_real():
    """Prueba INBURSA con formato real."""
    processor = GeminiProcessor()
    
    print("🧪 PROBANDO INBURSA CON FORMATO REAL")
    print("=" * 50)
    
    pdf_inbursa = crear_pdf_inbursa_real()
    resultado = processor.procesar_pdf(pdf_inbursa)
    
    print(f"✅ Éxito: {resultado.get('exito')}")
    print(f"🏦 Banco detectado: {resultado.get('banco_detectado')}")
    print(f"📊 Movimientos: {len(resultado.get('movimientos', []))}")
    print(f"🤖 Modelo utilizado: {resultado.get('modelo_utilizado')}")
    print(f"⏱️ Tiempo: {resultado.get('tiempo_procesamiento_segundos', 0):.2f}s")
    
    print("\n📋 Movimientos detectados:")
    for i, mov in enumerate(resultado.get('movimientos', [])):
        print(f"  {i+1}. {mov.get('fecha')} - {mov.get('concepto')[:50]}... - {mov.get('tipo_movimiento')} - ${mov.get('monto')}")
    
    # Limpiar archivo temporal
    if os.path.exists(pdf_inbursa):
        os.remove(pdf_inbursa)
    
    print(f"\n✅ Prueba completada! Se detectaron {len(resultado.get('movimientos', []))} movimientos")

if __name__ == "__main__":
    probar_inbursa_real() 