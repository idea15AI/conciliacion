#!/usr/bin/env python3
"""
Script para probar las mejoras en detección de bancos específicos:
- BANORTE: MONTO DEL DEPOSITO = ABONO, MONTO DEL RETIRO = CARGO
- BBVA: LIQUIDACION = SALDO
- INBURSA: Extracción completa de todos los movimientos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.gemini_processor import GeminiProcessor
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import tempfile

def crear_pdf_banorte_mejorado():
    """Crea un PDF de BANORTE con formato mejorado."""
    filename = "test_banorte_mejorado.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Encabezado
    c.drawString(50, height - 50, "BANORTE - ESTADO DE CUENTA")
    c.drawString(50, height - 70, "FECHA | DESCRIPCIÓN / ESTABLECIMIENTO | MONTO DEL DEPOSITO | MONTO DEL RETIRO | SALDO")
    
    # Movimientos
    movimientos = [
        ("01/MAY", "CUENTAS POR PAGAR - SAP", "1,000.00", "", "1,000.00"),
        ("02/MAY", "DISPOSICIONES EFECTIVO", "", "500.00", "500.00"),
        ("03/MAY", "DEPOSITO EN VENTANILLA", "2,000.00", "", "2,500.00"),
        ("04/MAY", "RETIRO EN CAJERO", "", "300.00", "2,200.00"),
        ("05/MAY", "PAGO DE SERVICIOS", "", "150.00", "2,050.00")
    ]
    
    y = height - 100
    for fecha, desc, deposito, retiro, saldo in movimientos:
        c.drawString(50, y, fecha)
        c.drawString(150, y, desc)
        c.drawString(350, y, deposito)
        c.drawString(450, y, retiro)
        c.drawString(550, y, saldo)
        y -= 20
    
    c.save()
    return filename

def crear_pdf_bbva_mejorado():
    """Crea un PDF de BBVA con liquidaciones."""
    filename = "test_bbva_mejorado.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Encabezado
    c.drawString(50, height - 50, "BBVA - ESTADO DE CUENTA")
    c.drawString(50, height - 70, "OPER | FECHA | SALDO | COD. | DESCRIPCIÓN | REFERENCIA")
    
    # Movimientos
    movimientos = [
        ("LIQ", "02/ABR", "1,000.00", "001", "LIQUIDACION INICIAL", "REF001"),
        ("DEP", "03/ABR", "2,000.00", "002", "DEPOSITO EFECTIVO", "REF002"),
        ("RET", "04/ABR", "500.00", "003", "RETIRO CAJERO", "REF003"),
        ("LIQ", "05/ABR", "2,500.00", "004", "LIQUIDACION FINAL", "REF004")
    ]
    
    y = height - 100
    for oper, fecha, saldo, cod, desc, ref in movimientos:
        c.drawString(50, y, oper)
        c.drawString(100, y, fecha)
        c.drawString(150, y, saldo)
        c.drawString(250, y, cod)
        c.drawString(300, y, desc)
        c.drawString(450, y, ref)
        y -= 20
    
    c.save()
    return filename

def crear_pdf_inbursa_completo():
    """Crea un PDF de INBURSA con todos los movimientos."""
    filename = "test_inbursa_completo.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Encabezado
    c.drawString(50, height - 50, "INBURSA - ESTADO DE CUENTA")
    c.drawString(50, height - 70, "FECHA | REFERENCIA | CONCEPTO | CARGOS | ABONOS | SALDO")
    
    # Movimientos completos
    movimientos = [
        ("MAY. 01", "3407784114", "BALANCE INICIAL", "", "", "44,432.09"),
        ("MAY. 02", "3407784114", "LIQUIDACION ADQUIRENTE CREDITO", "", "165.00", "44,597.09"),
        ("MAY. 02", "3407784117", "TASA DE DESCTO CREDITO", "4.60", "", "44,592.49"),
        ("MAY. 02", "3407784117", "IVA TASA DE DESCTO CREDITO", "0.74", "", "44,591.75"),
        ("MAY. 02", "3407784123", "LIQUIDACION ADQUIRENTE DEBITO", "", "1,050.00", "45,641.75"),
        ("MAY. 02", "3407784128", "TASA DE DESCTO DEBITO", "22.48", "", "45,619.27"),
        ("MAY. 02", "3407784128", "IVA TASA DE DESCTO DEBITO", "3.60", "", "45,615.67"),
        ("MAY. 08", "3408029858", "DEPOSITO TEF", "", "472.46", "46,088.13"),
        ("MAY. 05", "3411389231", "LIQUIDACION ADQUIRENTE DEBITO", "", "1,115.00", "47,203.13"),
        ("MAY. 05", "3411389232", "COMISION MANEJO CUENTA", "50.00", "", "47,153.13"),
        ("MAY. 06", "3411389233", "DEPOSITO SPEI", "", "2,000.00", "49,153.13"),
        ("MAY. 07", "3411389234", "RETIRO EFECTIVO", "1,000.00", "", "48,153.13")
    ]
    
    y = height - 100
    for fecha, ref, concepto, cargos, abonos, saldo in movimientos:
        c.drawString(50, y, fecha)
        c.drawString(120, y, ref)
        c.drawString(200, y, concepto)
        c.drawString(350, y, cargos)
        c.drawString(420, y, abonos)
        c.drawString(490, y, saldo)
        y -= 20
    
    c.save()
    return filename

def probar_mejoras():
    """Prueba las mejoras en detección de bancos."""
    processor = GeminiProcessor()
    
    print("🧪 PROBANDO MEJORAS EN DETECCIÓN DE BANCOS")
    print("=" * 60)
    
    # Probar BANORTE
    print("\n🏦 PROBANDO BANORTE:")
    pdf_banorte = crear_pdf_banorte_mejorado()
    resultado = processor.procesar_pdf(pdf_banorte)
    
    print(f"✅ Éxito: {resultado.get('exito')}")
    print(f"🏦 Banco detectado: {resultado.get('banco_detectado')}")
    print(f"📊 Movimientos: {len(resultado.get('movimientos', []))}")
    
    for i, mov in enumerate(resultado.get('movimientos', [])[:3]):
        print(f"  {i+1}. {mov.get('fecha')} - {mov.get('concepto')} - {mov.get('tipo_movimiento')}")
    
    # Probar BBVA
    print("\n🏦 PROBANDO BBVA:")
    pdf_bbva = crear_pdf_bbva_mejorado()
    resultado = processor.procesar_pdf(pdf_bbva)
    
    print(f"✅ Éxito: {resultado.get('exito')}")
    print(f"🏦 Banco detectado: {resultado.get('banco_detectado')}")
    print(f"📊 Movimientos: {len(resultado.get('movimientos', []))}")
    
    for i, mov in enumerate(resultado.get('movimientos', [])[:3]):
        print(f"  {i+1}. {mov.get('fecha')} - {mov.get('concepto')} - {mov.get('tipo_movimiento')}")
    
    # Probar INBURSA
    print("\n🏦 PROBANDO INBURSA:")
    pdf_inbursa = crear_pdf_inbursa_completo()
    resultado = processor.procesar_pdf(pdf_inbursa)
    
    print(f"✅ Éxito: {resultado.get('exito')}")
    print(f"🏦 Banco detectado: {resultado.get('banco_detectado')}")
    print(f"📊 Movimientos: {len(resultado.get('movimientos', []))}")
    
    for i, mov in enumerate(resultado.get('movimientos', [])[:5]):
        print(f"  {i+1}. {mov.get('fecha')} - {mov.get('concepto')} - {mov.get('tipo_movimiento')}")
    
    # Limpiar archivos temporales
    for filename in [pdf_banorte, pdf_bbva, pdf_inbursa]:
        if os.path.exists(filename):
            os.remove(filename)
    
    print("\n✅ Pruebas completadas!")

if __name__ == "__main__":
    probar_mejoras() 