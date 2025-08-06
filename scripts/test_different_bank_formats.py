#!/usr/bin/env python3
"""
Script para probar el procesador Gemini con diferentes formatos bancarios
"""

import os
import sys
import tempfile
import time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.gemini_processor import GeminiProcessor

def crear_pdf_bbva():
    """Crea un PDF con formato BBVA."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "EXTRACTO BANCARIO - BBVA")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 12)
    headers = ["FECHA", "COD.", "DESCRIPCIÓN", "REFERENCIA", "SALDO"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 100
        c.drawString(x, y, header)
    
    # Datos
    c.setFont("Helvetica", 10)
    data = [
        ["02/ABR", "RETIRO", "RETIRO EN CAJERO", "123456", "10,000.00"],
        ["02/ABR", "DEPOSITO", "DEPOSITO EN VENTANILLA", "789012", "12,500.00"],
        ["03/ABR", "COMISION", "COMISION POR SERVICIO", "345678", "9,950.00"],
        ["03/ABR", "TRANSFERENCIA", "TRANSFERENCIA SALIENTE", "901234", "8,950.00"]
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 100
            c.drawString(x, y, cell)
        y -= 20
    
    c.save()
    return filename

def crear_pdf_banorte():
    """Crea un PDF con formato BANORTE."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "EXTRACTO BANCARIO - BANORTE")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 12)
    headers = ["FECHA", "DESCRIPCIÓN / ESTABLECIMIENTO", "MONTO DEL DEPOSITO", "MONTO DEL RETIRO", "SALDO"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 90
        c.drawString(x, y, header)
    
    # Datos
    c.setFont("Helvetica", 10)
    data = [
        ["02/ABR", "DEPOSITO EN VENTANILLA", "5,000.00", "", "15,000.00"],
        ["02/ABR", "RETIRO EN CAJERO", "", "1,000.00", "14,000.00"],
        ["03/ABR", "COMISION POR SERVICIO", "", "50.00", "13,950.00"],
        ["03/ABR", "TRANSFERENCIA ENTRANTE", "2,500.00", "", "16,450.00"]
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 90
            c.drawString(x, y, cell)
        y -= 20
    
    c.save()
    return filename

def crear_pdf_banjio():
    """Crea un PDF con formato BANJIO."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "EXTRACTO BANCARIO - BANJIO")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 12)
    headers = ["FECHA", "DESCRIPCION DE LA OPERACION", "DEPOSITOS", "RETIROS", "SALDO"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 90
        c.drawString(x, y, header)
    
    # Datos
    c.setFont("Helvetica", 10)
    data = [
        ["02/ABR", "DEPOSITO EN VENTANILLA", "3,000.00", "", "13,000.00"],
        ["02/ABR", "RETIRO EN CAJERO", "", "500.00", "12,500.00"],
        ["03/ABR", "COMISION POR SERVICIO", "", "25.00", "12,475.00"],
        ["03/ABR", "TRANSFERENCIA ENTRANTE", "1,500.00", "", "13,975.00"]
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 90
            c.drawString(x, y, cell)
        y -= 20
    
    c.save()
    return filename

def crear_pdf_banamex():
    """Crea un PDF con formato BANAMEX."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "EXTRACTO BANCARIO - BANAMEX")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 12)
    headers = ["FECHA", "CONCEPTO", "GIRO DEL NEGOCIO", "POBLACIÓN / RFC", "MONEDA EXT.", "OTRAS DIVISAS", "PESOS"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 70
        c.drawString(x, y, header)
    
    # Datos
    c.setFont("Helvetica", 10)
    data = [
        ["02/ABR", "DEPOSITO", "DEPOSITO EN VENTANILLA", "MEXICO", "", "", "4,000.00"],
        ["02/ABR", "RETIRO", "RETIRO EN CAJERO", "MEXICO", "", "", "-800.00"],
        ["03/ABR", "COMISION", "COMISION POR SERVICIO", "MEXICO", "", "", "-30.00"],
        ["03/ABR", "TRANSFERENCIA", "TRANSFERENCIA ENTRANTE", "MEXICO", "", "", "2,000.00"]
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 70
            c.drawString(x, y, cell)
        y -= 20
    
    c.save()
    return filename

def probar_formato_bancario(nombre_banco, crear_func):
    """Prueba un formato bancario específico."""
    print(f"\n🏦 Probando formato: {nombre_banco}")
    print("=" * 50)
    
    try:
        # Crear PDF de prueba
        pdf_path = crear_func()
        print(f"✅ PDF creado: {pdf_path}")
        
        # Procesar con Gemini
        processor = GeminiProcessor()
        start_time = time.time()
        
        resultado = processor.procesar_pdf(pdf_path)
        tiempo_procesamiento = time.time() - start_time
        
        if resultado and resultado.get("exito"):
            movimientos = resultado.get("movimientos_extraidos", [])
            banco_detectado = resultado.get("banco_detectado", "Desconocido")
            
            print(f"✅ Éxito: {len(movimientos)} movimientos extraídos")
            print(f"🏦 Banco detectado: {banco_detectado}")
            print(f"⏱️  Tiempo: {tiempo_procesamiento:.1f}s")
            
            print(f"\n📋 Movimientos extraídos ({len(movimientos)}):")
            print("-" * 80)
            
            for i, mov in enumerate(movimientos, 1):
                fecha = mov.get("fecha", "N/A")
                referencia = mov.get("referencia", "N/A")
                concepto = mov.get("concepto", "N/A")
                monto = mov.get("monto", 0)
                tipo = mov.get("tipo_movimiento", "N/A")
                
                print(f" {i:2d}. {fecha} | {referencia:12s} | {concepto[:40]:40s} | ${monto:10.2f} | {tipo}")
                
        else:
            print(f"❌ Error: {resultado.get('error', 'Error desconocido')}")
            
    except Exception as e:
        print(f"❌ Error procesando {nombre_banco}: {e}")
    finally:
        # Limpiar archivo temporal
        if 'pdf_path' in locals():
            try:
                os.remove(pdf_path)
                print(f"🧹 Archivo temporal eliminado: {pdf_path}")
            except:
                pass

def main():
    """Función principal."""
    print("🧪 Test de Formatos Bancarios con Gemini")
    print("=" * 60)
    
    # Verificar configuración
    try:
        processor = GeminiProcessor()
        print("✅ Configuración de Gemini verificada")
    except Exception as e:
        print(f"❌ Error de configuración: {e}")
        return
    
    # Probar diferentes formatos bancarios
    formatos = [
        ("BBVA", crear_pdf_bbva),
        ("BANORTE", crear_pdf_banorte),
        ("BANJIO", crear_pdf_banjio),
        ("BANAMEX", crear_pdf_banamex)
    ]
    
    for nombre, crear_func in formatos:
        probar_formato_bancario(nombre, crear_func)
    
    print("\n" + "=" * 60)
    print("🎉 ¡Test de formatos bancarios completado!")

if __name__ == "__main__":
    main() 