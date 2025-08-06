#!/usr/bin/env python3
"""
Script para probar la detección mejorada de INBURSA
"""

import sys
import os
sys.path.append('/Users/ideasistemas/Desktop/conciliacion-main')

from app.conciliacion.gemini_processor import GeminiProcessor
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def crear_pdf_inbursa_test():
    """Crea un PDF de prueba con formato INBURSA"""
    c = canvas.Canvas("test_inbursa_format.pdf", pagesize=letter)
    
    # Título
    c.drawString(100, 750, "ESTADO DE CUENTA INBURSA")
    c.drawString(100, 730, "FORMATO DE PRUEBA")
    
    # Encabezados
    c.drawString(100, 700, "FECHA")
    c.drawString(200, 700, "REFERENCIA")
    c.drawString(350, 700, "CONCEPTO")
    c.drawString(500, 700, "MONTO")
    c.drawString(600, 700, "SALDO")
    
    # Línea separadora
    c.line(100, 690, 700, 690)
    
    # Movimientos de prueba basados en casos reales de INBURSA
    movimientos = [
        ("01/05/2025", None, "BALANCE INICIAL", "44432.09", "44432.09"),
        ("02/05/2025", "3407784114", "LIQUIDACION ADQUIRENTE CREDITO LIQUIDACION ADQ CREDITO-8993380", "165.00", "44597.09"),
        ("02/05/2025", "3407784117", "TASA DE DESCTO CREDITO APLICACION DE TASAS DE DESCUENTO-CREDITO-8993380", "4.60", "44592.49"),
        ("02/05/2025", "3407784117", "IVA TASA DE DESCTO CREDITO Tasa IVA 16.0 %", "0.74", "44591.75"),
        ("02/05/2025", "3407784123", "LIQUIDACION ADQUIRENTE DEBITO LIQUIDACION ADQ DEBITO-8993380", "1050.00", "45641.75"),
        ("02/05/2025", "3407784128", "TASA DE DESCTO DEBITO APLICACION DE TASAS DE DESCUENTO-DEBITO-8993380", "22.48", "45619.27"),
        ("02/05/2025", "3407784128", "IVA TASA DE DESCTO DEBITO Tasa IVA 16.0 %", "3.60", "45615.67"),
        ("02/05/2025", "3408029858", "DEPOSITO TEF 1041881046199 OPERADORA PAYPAL DE MEXICO S DE RL 106", "472.46", "46088.13"),
        ("05/05/2025", "3411389231", "LIQUIDACION ADQUIRENTE DEBITO LIQUIDACION ADQ DEBITO-8993380", "1115.00", "47203.13"),
    ]
    
    y_pos = 660
    for fecha, referencia, concepto, monto, saldo in movimientos:
        # Fecha
        c.drawString(100, y_pos, fecha)
        
        # Referencia
        ref_text = referencia if referencia else "N/A"
        c.drawString(200, y_pos, ref_text)
        
        # Concepto (corto)
        if len(concepto) > 30:
            concepto_corto = concepto[:30] + "..."
        else:
            concepto_corto = concepto
        c.drawString(350, y_pos, concepto_corto)
        
        # Monto
        c.drawString(500, y_pos, monto)
        
        # Saldo
        c.drawString(600, y_pos, saldo)
        
        y_pos -= 20
        
        # Si el concepto es largo, agregar línea adicional
        if len(concepto) > 30:
            y_pos -= 15
            c.drawString(350, y_pos, concepto[30:60] + "..." if len(concepto) > 60 else concepto[30:])
            y_pos -= 20
    
    c.save()
    print("✅ PDF con formato INBURSA creado: test_inbursa_format.pdf")

def probar_deteccion_inbursa():
    """Prueba la detección mejorada de INBURSA"""
    processor = GeminiProcessor()
    
    print("🧪 Probando detección mejorada de INBURSA...")
    
    resultado = processor.procesar_pdf('test_inbursa_format.pdf')
    
    if resultado.get('exito'):
        print(f"✅ Procesamiento exitoso")
        print(f"🏦 Banco detectado: {resultado.get('banco_detectado')}")
        print(f"📊 Total movimientos: {len(resultado.get('movimientos', []))}")
        print(f"⏱️ Tiempo: {resultado.get('tiempo_procesamiento_segundos', 0):.2f}s")
        
        # Mostrar primeros 3 movimientos
        for i, mov in enumerate(resultado.get('movimientos', [])[:3]):
            print(f"  {i+1}. {mov.get('fecha')} - {mov.get('concepto', '')[:50]}...")
            print(f"     Monto: {mov.get('monto')} | Tipo: {mov.get('tipo_movimiento')} | Saldo: {mov.get('saldo')}")
    else:
        print(f"❌ Error en procesamiento: {resultado.get('mensaje')}")

if __name__ == "__main__":
    crear_pdf_inbursa_test()
    probar_deteccion_inbursa() 