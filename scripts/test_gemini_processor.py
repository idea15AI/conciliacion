#!/usr/bin/env python3
"""
Script para probar el procesador de Gemini directamente.
"""

import sys
import os
import tempfile
import time

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def crear_pdf_ejemplo(file_path: str):
    """Crea un PDF de ejemplo con formato de extracto bancario."""
    
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    # Título
    elements.append(Paragraph("EXTRACTO BANCARIO - BANCO INBURSA", title_style))
    elements.append(Paragraph("", normal_style))  # Espacio
    
    # Datos del cliente
    elements.append(Paragraph("Cliente: EMPRESA EJEMPLO S.A. DE C.V.", normal_style))
    elements.append(Paragraph("Cuenta: 012345678901234567", normal_style))
    elements.append(Paragraph("Período: MAYO 2024", normal_style))
    elements.append(Paragraph("", normal_style))  # Espacio
    
    # Tabla de movimientos
    data = [
        ['FECHA', 'REFERENCIA', 'CONCEPTO', 'CARGOS', 'ABONOS', 'SALDO'],
        ['MAY. 01', '3407784114', 'BALANCE INICIAL', '', '', '44,432.09'],
        ['MAY. 02', '3407784117', 'LIQUIDACION ADQUIRENTE CREDITO', '165.00', '', '44,597.09'],
        ['MAY. 02', '3407784117', 'TASA DE DESCTO CREDITO', '4.60', '', '44,592.49'],
        ['MAY. 02', '3407784117', 'IVA TASA DE DESCTO CREDITO', '0.74', '', '44,591.75'],
        ['MAY. 02', '3407784123', 'LIQUIDACION ADQUIRENTE DEBITO', '1,050.00', '', '45,641.75'],
        ['MAY. 02', '3407784128', 'TASA DE DESCTO DEBITO', '22.48', '', '45,619.27'],
        ['MAY. 02', '3407784128', 'IVA TASA DE DESCTO DEBITO', '3.60', '', '45,615.67'],
        ['MAY. 02', '3408029858', 'DEPOSITO TEF', '', '472.46', '46,088.13'],
        ['MAY. 05', '3411389231', 'LIQUIDACION ADQUIRENTE DEBITO', '1,115.00', '', '47,203.13']
    ]
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Alinear montos a la derecha
    ]))
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    print(f"✅ PDF de ejemplo creado: {file_path}")

def main():
    """Función principal para probar el procesador de Gemini."""
    
    print("🧪 Test del Procesador Gemini")
    print("=" * 50)
    
    # Verificar configuración
    print("🔧 Verificando configuración de Gemini...")
    
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ Error: GEMINI_API_KEY no está configurada")
        return
    
    print("✅ GEMINI_API_KEY configurada")
    
    try:
        import google.genai
        print("✅ Librería google.genai disponible")
    except ImportError:
        print("❌ Error: Librería google.genai no está instalada")
        print("💡 Ejecuta: pip install google-genai")
        return
    
    # Crear PDF de ejemplo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        pdf_path = temp_file.name
    
    crear_pdf_ejemplo(pdf_path)
    print(f"✅ PDF de ejemplo creado: {os.path.basename(pdf_path)}")
    
    # Probar procesador
    print(f"🤖 Probando Gemini con: {os.path.basename(pdf_path)}")
    print("=" * 50)
    
    try:
        from app.conciliacion.gemini_processor import test_gemini_processor
        
        inicio = time.time()
        resultado = test_gemini_processor(pdf_path)
        tiempo = time.time() - inicio
        
        print("\n📊 RESULTADOS:")
        print("=" * 30)
        
        if resultado["exito"]:
            print("✅ Éxito: Procesado correctamente")
            print(f"📈 Total movimientos: {resultado['total_movimientos']}")
            print(f"🏦 Banco detectado: {resultado.get('banco_detectado', 'N/A')}")
            print(f"⏱️  Tiempo: {tiempo:.1f}s")
            print(f"🔧 Método: {resultado.get('metodo_usado', 'N/A')}")
            
            # Mostrar texto extraído
            if 'texto_extraido' in resultado:
                print(f"\n📄 Texto extraído (primeros 500 chars):")
                print("-" * 50)
                print(resultado['texto_extraido'])
                print("-" * 50)
            
            # Mostrar movimientos
            movimientos = resultado.get("movimientos_extraidos", [])
            if movimientos:
                print(f"\n📋 Movimientos extraídos ({len(movimientos)}):")
                print("-" * 80)
                for i, mov in enumerate(movimientos, 1):
                    print(f"{i:2d}. {mov.get('fecha', 'N/A')} | {mov.get('referencia', ''):<12} | {mov.get('concepto', 'N/A'):<30} | ${mov.get('monto', 0):>10.2f} | {mov.get('tipo_movimiento', 'N/A')}")
            else:
                print("\n⚠️ No se extrajeron movimientos")
        else:
            print("❌ Error: Procesamiento falló")
            print(f"🔍 Error: {resultado.get('error', 'Error desconocido')}")
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(pdf_path)
            print(f"\n🧹 Archivo temporal eliminado: {os.path.basename(pdf_path)}")
        except:
            pass
    
    print("\n" + "=" * 50)
    print("🎉 ¡Test completado exitosamente!")

if __name__ == "__main__":
    main() 