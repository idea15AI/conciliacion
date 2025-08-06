#!/usr/bin/env python3
"""
Script para probar específicamente BANORTE con casos especiales
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

def crear_pdf_banorte_casos_especiales():
    """Crea un PDF con casos especiales de BANORTE."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "BANORTE - CASOS ESPECIALES")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 12)
    headers = ["FECHA", "DESCRIPCIÓN", "MONTO DEL DEPOSITO", "MONTO DEL RETIRO", "SALDO"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 90
        c.drawString(x, y, header)
    
    # Datos con casos especiales
    c.setFont("Helvetica", 10)
    data = [
        ["MAY. 02", "LIQUIDACION ADQUIRENTE DEBITO", "1,050.00", "", "45,641.75"],
        ["MAY. 02", "LIQUIDACION ADQUIRENTE CREDITO", "", "165.00", "45,476.75"],
        ["MAY. 02", "TASA DE DESCTO CREDITO", "", "4.60", "45,472.15"],
        ["MAY. 02", "TASA DE DESCTO DEBITO", "", "22.48", "45,449.67"],
        ["MAY. 02", "IVA TASA DE DESCTO CREDITO", "", "0.74", "45,448.93"],
        ["MAY. 02", "IVA TASA DE DESCTO DEBITO", "", "3.60", "45,445.33"],
        ["MAY. 02", "DEPOSITO TEF", "472.46", "", "45,917.79"],
        ["MAY. 05", "LIQUIDACION ADQUIRENTE DEBITO", "1,115.00", "", "47,032.79"]
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 90
            c.drawString(x, y, cell)
        y -= 20
    
    c.save()
    return filename

def crear_pdf_banorte_confusion():
    """Crea un PDF con casos que pueden causar confusión en BANORTE."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "BANORTE - CASOS CONFUSOS")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 12)
    headers = ["FECHA", "DESCRIPCIÓN", "MONTO DEL DEPOSITO", "MONTO DEL RETIRO", "SALDO"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 90
        c.drawString(x, y, header)
    
    # Datos confusos - conceptos que dicen una cosa pero están en columnas diferentes
    c.setFont("Helvetica", 10)
    data = [
        ["MAY. 02", "CREDITO EN CUENTA", "", "100.00", "44,900.00"],  # Dice CREDITO pero está en RETIRO
        ["MAY. 02", "DEBITO POR SERVICIO", "500.00", "", "45,400.00"],  # Dice DEBITO pero está en DEPOSITO
        ["MAY. 02", "ABONO POR TRANSFERENCIA", "", "50.00", "45,350.00"],  # Dice ABONO pero está en RETIRO
        ["MAY. 02", "CARGO POR COMISION", "200.00", "", "45,550.00"],  # Dice CARGO pero está en DEPOSITO
        ["MAY. 02", "INGRESO POR DEPOSITO", "", "75.00", "45,475.00"],  # Dice INGRESO pero está en RETIRO
        ["MAY. 02", "RETIRO EN CAJERO", "300.00", "", "45,775.00"]  # Dice RETIRO pero está en DEPOSITO
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 90
            c.drawString(x, y, cell)
        y -= 20
    
    c.save()
    return filename

def probar_banorte(nombre_test, crear_func):
    """Prueba un caso específico de BANORTE."""
    print(f"\n🏦 Probando BANORTE: {nombre_test}")
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
            print("-" * 120)
            
            for i, mov in enumerate(movimientos, 1):
                fecha = mov.get("fecha", "N/A")
                referencia = mov.get("referencia", "N/A")
                concepto = mov.get("concepto", "N/A")
                monto = mov.get("monto", 0)
                tipo = mov.get("tipo_movimiento", "N/A")
                saldo = mov.get("saldo", 0)
                
                print(f" {i:2d}. {fecha} | {referencia:12s} | {concepto[:60]:60s} | ${monto:10.2f} | {tipo:6s} | ${saldo:10.2f}")
                
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
                
                if "TASA DE DESCTO CREDITO" in concepto.upper():
                    if tipo == "cargo":
                        print(f"    ✅ CORRECTO: TASA DE DESCTO CREDITO detectado como CARGO")
                    else:
                        print(f"    ❌ INCORRECTO: TASA DE DESCTO CREDITO detectado como {tipo.upper()}")
                
                # Verificar casos confusos
                if "CREDITO" in concepto.upper() and tipo == "cargo":
                    print(f"    ✅ CORRECTO: Concepto con CREDITO detectado como CARGO (por columna)")
                elif "DEBITO" in concepto.upper() and tipo == "abono":
                    print(f"    ✅ CORRECTO: Concepto con DEBITO detectado como ABONO (por columna)")
                
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
    print("🧪 Test Específico de BANORTE con Gemini")
    print("=" * 60)
    
    # Verificar configuración
    try:
        processor = GeminiProcessor()
        print("✅ Configuración de Gemini verificada")
    except Exception as e:
        print(f"❌ Error de configuración: {e}")
        return
    
    # Probar casos específicos de BANORTE
    casos = [
        ("Casos Especiales", crear_pdf_banorte_casos_especiales),
        ("Casos Confusos", crear_pdf_banorte_confusion)
    ]
    
    for nombre, crear_func in casos:
        probar_banorte(nombre, crear_func)
    
    print("\n" + "=" * 60)
    print("🎉 ¡Test específico de BANORTE completado!")

if __name__ == "__main__":
    main() 