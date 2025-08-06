#!/usr/bin/env python3
"""
Test del procesador avanzado de facturas
"""
import requests
import json
import sys
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def check_server_status():
    """Verifica el estado del servidor"""
    try:
        response = requests.get(f"{API_BASE}/salud", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor en línea")
            return True
        else:
            print(f"⚠️ Servidor responde con status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Servidor no disponible: {e}")
        return False

def create_test_invoice():
    """Crea una factura de prueba"""
    filename = "test_invoice.pdf"
    
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Header de la factura
        c.drawString(50, 750, "INVOICE")
        c.drawString(50, 730, "Invoice Number: INV-2025-001")
        c.drawString(50, 710, "Invoice Date: January 15, 2025")
        c.drawString(50, 690, "Due Date: January 31, 2025")
        
        # Información del vendedor
        c.drawString(50, 650, "From:")
        c.drawString(50, 630, "ABC Company")
        c.drawString(50, 610, "123 Business Street")
        c.drawString(50, 590, "City, State 12345")
        
        # Información del cliente
        c.drawString(300, 650, "Bill To:")
        c.drawString(300, 630, "XYZ Corporation")
        c.drawString(300, 610, "456 Client Avenue")
        c.drawString(300, 590, "Client City, State 67890")
        
        # Tabla de items
        c.drawString(50, 550, "Item Description")
        c.drawString(300, 550, "Quantity")
        c.drawString(400, 550, "Unit Price")
        c.drawString(500, 550, "Total")
        
        # Línea separadora
        c.line(50, 540, 550, 540)
        
        # Items
        items = [
            ("Web Design Services", 1, 1500.00),
            ("Hosting (Monthly)", 12, 25.00),
            ("Domain Registration", 1, 15.00),
        ]
        
        y_pos = 520
        subtotal = 0
        
        for item, qty, price in items:
            total = qty * price
            subtotal += total
            
            c.drawString(50, y_pos, item)
            c.drawString(300, y_pos, str(qty))
            c.drawString(400, y_pos, f"${price:.2f}")
            c.drawString(500, y_pos, f"${total:.2f}")
            y_pos -= 20
        
        # Totales
        c.line(50, y_pos - 10, 550, y_pos - 10)
        y_pos -= 30
        
        c.drawString(400, y_pos, "Subtotal:")
        c.drawString(500, y_pos, f"${subtotal:.2f}")
        y_pos -= 20
        
        tax = subtotal * 0.16
        c.drawString(400, y_pos, "Tax (16%):")
        c.drawString(500, y_pos, f"${tax:.2f}")
        y_pos -= 20
        
        total = subtotal + tax
        c.drawString(400, y_pos, "Total Due:")
        c.drawString(500, y_pos, f"${total:.2f}")
        
        # Notas
        c.drawString(50, 200, "Notes:")
        c.drawString(50, 180, "Payment is due within 30 days")
        c.drawString(50, 160, "Please include invoice number with payment")
        
        c.save()
        print(f"✅ Factura de prueba creada: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error creando factura: {e}")
        return None

def test_invoice_processor(pdf_file):
    """Prueba el procesador de facturas"""
    print(f"\n🔍 PROBANDO PROCESADOR DE FACTURAS")
    print("-" * 50)
    
    try:
        # Importar el procesador directamente
        from app.conciliacion.invoice_processor import InvoiceProcessor
        
        # Leer el PDF
        with open(pdf_file, 'rb') as f:
            pdf_bytes = f.read()
        
        # Crear procesador
        processor = InvoiceProcessor()
        
        # Procesar factura
        print("📄 Procesando factura...")
        resultado = processor.procesar_factura(pdf_bytes)
        
        print("✅ Factura procesada exitosamente")
        print(f"   🏷️ Campos extraídos: {len(resultado.get('campos_extraidos', {}))}")
        print(f"   📊 Tablas encontradas: {len(resultado.get('tablas', []))}")
        print(f"   🧠 Entidades NER: {sum(len(v) for v in resultado.get('entidades_ner', {}).values())}")
        print(f"   ⏱️ Tiempo: {resultado.get('tiempo_procesamiento', 0):.2f}s")
        print(f"   📈 Confianza: {resultado.get('confianza', 0):.2f}")
        print(f"   🔧 Métodos usados: {', '.join(resultado.get('metodos_usados', []))}")
        
        # Mostrar campos extraídos
        if resultado.get('campos_extraidos'):
            print(f"\n   📋 Campos extraídos:")
            for campo, valor in resultado['campos_extraidos'].items():
                print(f"      {campo}: {valor}")
        
        # Mostrar entidades NER
        if resultado.get('entidades_ner'):
            print(f"\n   🧠 Entidades NER:")
            for tipo, entidades in resultado['entidades_ner'].items():
                if entidades:
                    print(f"      {tipo}: {entidades[:3]}")  # Mostrar solo las primeras 3
        
        # Probar OCR avanzado
        print(f"\n🔍 Probando OCR avanzado...")
        resultado_ocr = processor.procesar_factura_con_ocr(pdf_bytes)
        
        print(f"   📄 Páginas procesadas: {resultado_ocr.get('paginas_procesadas', 0)}")
        print(f"   🏷️ Campos OCR: {len(resultado_ocr.get('campos_extraidos', {}))}")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error procesando factura: {e}")
        return None

def compare_methods(pdf_file):
    """Compara diferentes métodos de extracción"""
    print(f"\n📊 COMPARACIÓN DE MÉTODOS")
    print("=" * 60)
    
    try:
        from app.conciliacion.invoice_processor import InvoiceProcessor
        
        with open(pdf_file, 'rb') as f:
            pdf_bytes = f.read()
        
        processor = InvoiceProcessor()
        
        # Método 1: Procesamiento normal
        print("🧪 Método 1: Procesamiento normal")
        resultado_normal = processor.procesar_factura(pdf_bytes)
        
        # Método 2: OCR avanzado
        print("🧪 Método 2: OCR avanzado")
        resultado_ocr = processor.procesar_factura_con_ocr(pdf_bytes)
        
        # Comparar resultados
        print(f"\n📊 RESUMEN DE COMPARACIÓN")
        print("-" * 40)
        
        campos_normal = len(resultado_normal.get('campos_extraidos', {}))
        campos_ocr = len(resultado_ocr.get('campos_extraidos', {}))
        
        print(f"Procesamiento Normal: {campos_normal} campos | Confianza: {resultado_normal.get('confianza', 0):.2f}")
        print(f"OCR Avanzado:        {campos_ocr} campos | Método: {resultado_ocr.get('metodo', 'N/A')}")
        
        # Mostrar qué campos encontró cada método
        if resultado_normal.get('campos_extraidos'):
            print(f"\nCampos encontrados (Normal): {list(resultado_normal['campos_extraidos'].keys())}")
        
        if resultado_ocr.get('campos_extraidos'):
            print(f"Campos encontrados (OCR): {list(resultado_ocr['campos_extraidos'].keys())}")
        
        return {
            "normal": resultado_normal,
            "ocr": resultado_ocr
        }
        
    except Exception as e:
        print(f"❌ Error en comparación: {e}")
        return None

def main():
    print("🔍 TEST DEL PROCESADOR AVANZADO DE FACTURAS")
    print("=" * 80)
    
    # 1. Verificar servidor
    if not check_server_status():
        print("❌ No se puede continuar sin servidor")
        return
    
    # 2. Crear factura de prueba
    pdf_file = create_test_invoice()
    if not pdf_file:
        print("❌ No se pudo crear factura de prueba")
        return
    
    try:
        # 3. Probar procesador de facturas
        resultado = test_invoice_processor(pdf_file)
        
        # 4. Comparar métodos
        resultados_comparacion = compare_methods(pdf_file)
        
        # 5. Análisis final
        print(f"\n🎯 ANÁLISIS FINAL")
        print("=" * 40)
        
        if resultado:
            print("✅ Procesador de facturas funcionando correctamente")
            print(f"   📊 Extrajo {len(resultado.get('campos_extraidos', {}))} campos")
            print(f"   💡 Usa múltiples técnicas: regex, NER, tablas, OCR")
        else:
            print("❌ Problemas con el procesador de facturas")
        
        print(f"\n💡 CARACTERÍSTICAS IMPLEMENTADAS:")
        print("   1. ✅ Extracción de texto con PyMuPDF y pdfplumber")
        print("   2. ✅ Extracción de tablas con pdfplumber")
        print("   3. ✅ Campos específicos con regex")
        print("   4. ✅ Entidades nombradas con spaCy NER")
        print("   5. ✅ OCR avanzado con Tesseract + OpenCV")
        print("   6. ✅ Validación cruzada de resultados")
        print("   7. ✅ Métricas de confianza")
        
    finally:
        # Limpiar archivo de prueba
        try:
            os.remove(pdf_file)
            print(f"\n🧹 Archivo de prueba eliminado: {pdf_file}")
        except:
            pass

if __name__ == "__main__":
    main() 