#!/usr/bin/env python3
"""
Script para diagnosticar por qué no se extraen movimientos del PDF de Inbursa
"""
import sys
import os
import io
import pdfplumber
import fitz  # PyMuPDF
import re
from datetime import datetime

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.pdf_processor import PDFProcessor

def analizar_pdf_detallado(archivo_pdf):
    """Análisis detallado del PDF para entender su estructura"""
    
    print(f"🔍 ANÁLISIS DETALLADO DEL PDF: {archivo_pdf}")
    print("=" * 80)
    
    if not os.path.exists(archivo_pdf):
        print(f"❌ El archivo {archivo_pdf} no existe")
        return
    
    try:
        # Leer el archivo
        with open(archivo_pdf, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"📁 Archivo leído: {len(pdf_bytes)} bytes")
        
        # === ANÁLISIS CON PDFPLUMBER ===
        print("\n🔍 ANÁLISIS CON PDFPLUMBER:")
        print("-" * 50)
        
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            print(f"📄 Total de páginas: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n📄 PÁGINA {page_num}:")
                
                # Extraer texto
                texto = page.extract_text()
                if texto:
                    print(f"   📝 Texto extraído: {len(texto)} caracteres")
                    
                    # Mostrar primeras líneas
                    lineas = texto.split('\n')[:15]
                    print(f"   📋 Primeras 15 líneas:")
                    for i, linea in enumerate(lineas, 1):
                        if linea.strip():
                            print(f"      {i:2}: {linea.strip()[:80]}")
                    
                    # Buscar patrones de fecha
                    fechas = re.findall(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', texto)
                    print(f"   📅 Fechas encontradas: {len(fechas)} - {fechas[:5]}")
                    
                    # Buscar patrones de dinero
                    montos = re.findall(r'[\d,]+\.\d{2}', texto)
                    print(f"   💰 Montos encontrados: {len(montos)} - {montos[:5]}")
                    
                    # Buscar líneas que contengan fecha Y monto
                    lineas_con_movimiento = []
                    for linea in lineas:
                        if re.search(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', linea) and re.search(r'[\d,]+\.\d{2}', linea):
                            lineas_con_movimiento.append(linea.strip())
                    
                    print(f"   🎯 Líneas con fecha+monto: {len(lineas_con_movimiento)}")
                    for i, linea in enumerate(lineas_con_movimiento[:5], 1):
                        print(f"      M{i}: {linea[:100]}")
                
                else:
                    print(f"   ⚠️ No se pudo extraer texto de la página {page_num}")
                
                # Extraer tablas
                tablas = page.extract_tables()
                print(f"   📊 Tablas detectadas: {len(tablas)}")
                
                for i, tabla in enumerate(tablas, 1):
                    print(f"      Tabla {i}: {len(tabla)} filas x {len(tabla[0]) if tabla else 0} columnas")
                    if tabla:
                        # Mostrar primera fila (header)
                        print(f"         Header: {tabla[0]}")
                        # Mostrar primera fila de datos
                        if len(tabla) > 1:
                            print(f"         Datos:  {tabla[1]}")
        
        # === ANÁLISIS CON NUESTRO PROCESSOR ===
        print(f"\n🤖 ANÁLISIS CON NUESTRO PDFProcessor:")
        print("-" * 50)
        
        processor = PDFProcessor()
        resultado = processor.procesar_estado_cuenta(pdf_bytes, empresa_id=1)
        
        print(f"   ✅ Éxito: {resultado['exito']}")
        print(f"   🏦 Banco detectado: {resultado.get('banco_detectado', 'No detectado')}")
        print(f"   📊 Movimientos extraídos: {resultado.get('total_movimientos', 0)}")
        print(f"   ⏱️ Tiempo de procesamiento: {resultado.get('tiempo_procesamiento', 0)}s")
        
        if resultado.get('errores'):
            print(f"   ❌ Errores: {resultado['errores']}")
        
        if resultado.get('estadisticas'):
            print(f"   📈 Estadísticas: {resultado['estadisticas']}")
        
        # Mostrar metadatos si están disponibles
        if resultado.get('metadatos'):
            metadatos = resultado['metadatos']
            print(f"   📋 Metadatos extraídos:")
            for key, value in metadatos.items():
                print(f"      {key}: {value}")
        
        print(f"\n{'='*80}")
        print(f"🎯 DIAGNÓSTICO COMPLETADO")
        
    except Exception as e:
        print(f"❌ Error en el análisis: {str(e)}")
        import traceback
        traceback.print_exc()

def buscar_archivo_inbursa():
    """Busca archivos PDF de Inbursa en el directorio actual"""
    archivos_encontrados = []
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pdf') and 'INBURSA' in file.upper():
                archivos_encontrados.append(os.path.join(root, file))
    
    return archivos_encontrados

def main():
    print("🔍 DIAGNÓSTICO DE PDF DE INBURSA")
    print("=" * 80)
    
    # Buscar archivos de Inbursa
    archivos_inbursa = buscar_archivo_inbursa()
    
    if archivos_inbursa:
        print(f"📁 Archivos de Inbursa encontrados:")
        for i, archivo in enumerate(archivos_inbursa, 1):
            print(f"   {i}. {archivo}")
        
        # Analizar el primer archivo encontrado
        archivo_a_analizar = archivos_inbursa[0]
        print(f"\n🎯 Analizando: {archivo_a_analizar}")
        analizar_pdf_detallado(archivo_a_analizar)
    else:
        print("❌ No se encontraron archivos PDF de Inbursa")
        print("💡 Coloca tu archivo MAYO_2025_INBURSA_IDE2001209V6.pdf en el directorio actual")
        
        # Revisar archivos PDF disponibles
        pdfs_disponibles = [f for f in os.listdir('.') if f.endswith('.pdf')]
        if pdfs_disponibles:
            print(f"\n📁 PDFs disponibles:")
            for pdf in pdfs_disponibles:
                print(f"   - {pdf}")
            
            # Si hay solo uno, analizarlo
            if len(pdfs_disponibles) == 1:
                print(f"\n🎯 Analizando único PDF disponible: {pdfs_disponibles[0]}")
                analizar_pdf_detallado(pdfs_disponibles[0])

if __name__ == "__main__":
    main()