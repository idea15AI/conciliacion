#!/usr/bin/env python3
"""
Script para analizar el PDF real del usuario y ver por qué no extrae movimientos
"""
import sys
import os
import io
import pdfplumber
import re
from datetime import datetime

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_pdf_text(pdf_path):
    """Analiza el texto del PDF línea por línea"""
    
    print(f"🔍 ANALIZANDO: {pdf_path}")
    print("=" * 80)
    
    if not os.path.exists(pdf_path):
        print(f"❌ Archivo no encontrado: {pdf_path}")
        return
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"📁 Archivo leído: {len(pdf_bytes)} bytes")
        
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            print(f"📄 Total de páginas: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n📄 PÁGINA {page_num}:")
                print("-" * 50)
                
                # Extraer texto
                texto = page.extract_text()
                if texto:
                    lineas = texto.split('\n')
                    print(f"📝 Total de líneas: {len(lineas)}")
                    
                    # Analizar cada línea
                    movimientos_detectados = 0
                    
                    for i, linea in enumerate(lineas, 1):
                        linea = linea.strip()
                        if len(linea) < 5:
                            continue
                        
                        # Mostrar todas las líneas con contenido
                        print(f"   {i:3}: {linea}")
                        
                        # Verificar si parece un movimiento
                        tiene_fecha = check_fecha_patterns(linea)
                        tiene_monto = check_monto_patterns(linea)
                        
                        if tiene_fecha and tiene_monto:
                            print(f"        🎯 POSIBLE MOVIMIENTO DETECTADO!")
                            print(f"        📅 Fechas: {tiene_fecha}")
                            print(f"        💰 Montos: {tiene_monto}")
                            movimientos_detectados += 1
                        elif tiene_fecha:
                            print(f"        📅 Solo fecha: {tiene_fecha}")
                        elif tiene_monto:
                            print(f"        💰 Solo monto: {tiene_monto}")
                        
                        # Limitar output para no saturar
                        if i > 30:
                            print(f"   ... (mostrando solo primeras 30 líneas)")
                            break
                    
                    print(f"\n📊 RESUMEN PÁGINA {page_num}:")
                    print(f"   📝 Líneas analizadas: {min(len(lineas), 30)}")
                    print(f"   🎯 Posibles movimientos: {movimientos_detectados}")
                    
                    # Analizar tablas
                    tablas = page.extract_tables()
                    print(f"   📊 Tablas detectadas: {len(tablas)}")
                    
                    if tablas:
                        for j, tabla in enumerate(tablas, 1):
                            print(f"      Tabla {j}: {len(tabla)} filas")
                            if tabla and len(tabla) > 0:
                                print(f"         Columnas: {len(tabla[0])}")
                                print(f"         Primera fila: {tabla[0]}")
                                if len(tabla) > 1:
                                    print(f"         Segunda fila: {tabla[1]}")
                
                else:
                    print(f"   ⚠️ No se pudo extraer texto de la página {page_num}")
        
        print(f"\n{'='*80}")
        print("🎯 ANÁLISIS COMPLETADO")
        
    except Exception as e:
        print(f"❌ Error en el análisis: {str(e)}")
        import traceback
        traceback.print_exc()

def check_fecha_patterns(linea):
    """Verifica patrones de fecha en una línea"""
    patrones = [
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',          # DD/MM/YYYY
        r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',          # DD-MM-YYYY
        r'\b\d{1,2}\s+\d{1,2}\s+\d{2,4}\b',      # DD MM YYYY
        r'\b\d{4}/\d{1,2}/\d{1,2}\b',            # YYYY/MM/DD
        r'\b\d{4}-\d{1,2}-\d{1,2}\b',            # YYYY-MM-DD
        r'\b\d{1,2}\s+(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\s+\d{2,4}\b',  # DD MMM YYYY
    ]
    
    fechas_encontradas = []
    for patron in patrones:
        matches = re.findall(patron, linea, re.IGNORECASE)
        fechas_encontradas.extend(matches)
    
    return fechas_encontradas if fechas_encontradas else None

def check_monto_patterns(linea):
    """Verifica patrones de monto en una línea"""
    patrones = [
        r'[\d,]+\.\d{2}',                    # 1,234.56
        r'\d+\.\d{2}',                       # 1234.56
        r'[\d,]{3,}',                        # 1,234 (sin decimales, mínimo 3 dígitos)
        r'\$\s*[\d,]+\.?\d*',                # $1,234.56
        r'[\d\s,]+\.\d{2}',                  # 1 234.56
        r'\b\d{1,3}(?:,\d{3})*\b',          # Formato con comas cada 3 dígitos
    ]
    
    montos_encontrados = []
    for patron in patrones:
        matches = re.findall(patron, linea)
        montos_encontrados.extend(matches)
    
    return montos_encontrados if montos_encontrados else None

def find_pdf_files():
    """Busca archivos PDF en el directorio actual"""
    pdf_files = []
    
    # Buscar en directorio actual
    for file in os.listdir('.'):
        if file.endswith('.pdf'):
            pdf_files.append(file)
    
    # Buscar específicamente archivos de Inbursa
    inbursa_files = [f for f in pdf_files if 'INBURSA' in f.upper()]
    
    return pdf_files, inbursa_files

def main():
    print("🔍 ANÁLISIS DETALLADO DE PDF - DIAGNÓSTICO DE EXTRACCIÓN")
    print("=" * 80)
    
    # Buscar archivos PDF
    pdf_files, inbursa_files = find_pdf_files()
    
    if inbursa_files:
        print(f"📁 Archivos de Inbursa encontrados:")
        for i, archivo in enumerate(inbursa_files, 1):
            print(f"   {i}. {archivo}")
        
        # Analizar el primer archivo de Inbursa
        archivo_a_analizar = inbursa_files[0]
        print(f"\n🎯 Analizando archivo de Inbursa: {archivo_a_analizar}")
        analyze_pdf_text(archivo_a_analizar)
        
    elif pdf_files:
        print(f"📁 Archivos PDF encontrados:")
        for i, archivo in enumerate(pdf_files, 1):
            print(f"   {i}. {archivo}")
        
        # Analizar el primer archivo
        archivo_a_analizar = pdf_files[0]
        print(f"\n🎯 Analizando primer PDF: {archivo_a_analizar}")
        analyze_pdf_text(archivo_a_analizar)
        
    else:
        print("❌ No se encontraron archivos PDF")
        print("💡 Por favor, coloca tu archivo MAYO_2025_INBURSA_IDE2001209V6.pdf en este directorio")
        print(f"📂 Directorio actual: {os.getcwd()}")
        
        # Mostrar archivos disponibles
        files = os.listdir('.')
        print(f"\n📁 Archivos disponibles:")
        for f in files:
            if os.path.isfile(f):
                print(f"   - {f}")

if __name__ == "__main__":
    main()