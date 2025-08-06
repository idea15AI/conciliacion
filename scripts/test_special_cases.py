#!/usr/bin/env python3
"""
Script para probar casos especiales del procesador Gemini
"""

import os
import sys
import tempfile
import time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.gemini_processor import GeminiProcessor

def crear_pdf_caso_especial():
    """Crea un PDF con el caso especial mencionado por el usuario."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "CASO ESPECIAL - LIQUIDACION ADQUIRENTE DEBITO")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 12)
    headers = ["FECHA", "REFERENCIA", "CONCEPTO", "MONTO", "TIPO", "SALDO"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 90
        c.drawString(x, y, header)
    
    # Datos del caso especial
    c.setFont("Helvetica", 10)
    data = [
        ["MAY. 02", "3407784123", "LIQUIDACION ADQUIRENTE DEBITO", "1,050.00", "ABONO", "45,641.75"],
        ["MAY. 02", "3407784117", "LIQUIDACION ADQUIRENTE CREDITO", "165.00", "CARGO", "44,432.09"],
        ["MAY. 02", "3407784117", "TASA DE DESCTO CREDITO", "4.60", "CARGO", "44,427.49"],
        ["MAY. 02", "3407784117", "IVA TASA DE DESCTO CREDITO", "0.74", "CARGO", "44,426.75"]
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 90
            c.drawString(x, y, cell)
        y -= 20
    
    c.save()
    return filename

def crear_pdf_formato_banorte():
    """Crea un PDF con formato BANORTE para probar detección por columnas."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "BANORTE - CASO ESPECIAL")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 12)
    headers = ["FECHA", "DESCRIPCIÓN", "MONTO DEL DEPOSITO", "MONTO DEL RETIRO", "SALDO"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 90
        c.drawString(x, y, header)
    
    # Datos - Caso especial donde LIQUIDACION ADQUIRENTE DEBITO está en columna de depósito
    c.setFont("Helvetica", 10)
    data = [
        ["MAY. 02", "LIQUIDACION ADQUIRENTE DEBITO", "1,050.00", "", "45,641.75"],
        ["MAY. 02", "LIQUIDACION ADQUIRENTE CREDITO", "", "165.00", "45,476.75"],
        ["MAY. 02", "TASA DE DESCTO CREDITO", "", "4.60", "45,472.15"],
        ["MAY. 02", "DEPOSITO TEF", "472.46", "", "45,944.61"]
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 90
            c.drawString(x, y, cell)
        y -= 20
    
    c.save()
    return filename

def probar_caso_especial(nombre_test, crear_func):
    """Prueba un caso especial específico."""
    print(f"\n🧪 Probando caso especial: {nombre_test}")
    print("=" * 60)
    
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
            print("-" * 100)
            
            for i, mov in enumerate(movimientos, 1):
                fecha = mov.get("fecha", "N/A")
                referencia = mov.get("referencia", "N/A")
                concepto = mov.get("concepto", "N/A")
                monto = mov.get("monto", 0)
                tipo = mov.get("tipo_movimiento", "N/A")
                saldo = mov.get("saldo", 0)
                
                print(f" {i:2d}. {fecha} | {referencia:12s} | {concepto[:50]:50s} | ${monto:10.2f} | {tipo:6s} | ${saldo:10.2f}")
                
                # Verificar casos especiales
                if "LIQUIDACION ADQUIRENTE DEBITO" in concepto.upper():
                    if tipo == "abono":
                        print(f"    ✅ CORRECTO: LIQUIDACION ADQUIRENTE DEBITO detectado como ABONO")
                    else:
                        print(f"    ❌ INCORRECTO: LIQUIDACION ADQUIRENTE DEBITO detectado como {tipo.upper()}")
                
                if "LIQUIDACION ADQUIRENTE CREDITO" in concepto.upper():
                    if tipo == "cargo":
                        print(f"    ✅ CORRECTO: LIQUIDACION ADQUIRENTE CREDITO detectado como CARGO")
                    else:
                        print(f"    ❌ INCORRECTO: LIQUIDACION ADQUIRENTE CREDITO detectado como {tipo.upper()}")
                
        else:
            print(f"❌ Error: {resultado.get('error', 'Error desconocido')}")
            
    except Exception as e:
        print(f"❌ Error procesando {nombre_test}: {e}")
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
    print("🧪 Test de Casos Especiales con Gemini")
    print("=" * 60)
    
    # Verificar configuración
    try:
        processor = GeminiProcessor()
        print("✅ Configuración de Gemini verificada")
    except Exception as e:
        print(f"❌ Error de configuración: {e}")
        return
    
    # Probar casos especiales
    casos = [
        ("Caso Especial - LIQUIDACION ADQUIRENTE DEBITO", crear_pdf_caso_especial),
        ("BANORTE - Detección por Columnas", crear_pdf_formato_banorte)
    ]
    
    for nombre, crear_func in casos:
        probar_caso_especial(nombre, crear_func)
    
    print("\n" + "=" * 60)
    print("🎉 ¡Test de casos especiales completado!")

if __name__ == "__main__":
    main() 