#!/usr/bin/env python3
"""
Test específico para diferentes formatos de PDF de Inbursa
"""
import sys
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.pdf_processor import PDFProcessor

def create_inbursa_format_tests():
    """Crea PDFs con diferentes formatos que usa Inbursa"""
    
    test_formats = [
        {
            "name": "inbursa_format_1.pdf",
            "description": "Formato tradicional DD/MM/YYYY",
            "content": [
                "GRUPO FINANCIERO INBURSA",
                "ESTADO DE CUENTA MAYO 2025",
                "CUENTA: 123456789 - IDE2001209V6",
                "PERIODO: 01/05/2025 AL 31/05/2025",
                "",
                "FECHA      DESCRIPCION                      CARGO       ABONO      SALDO",
                "02/05/2025 DEPOSITO EN EFECTIVO                         5,000.00   30,000.00",
                "03/05/2025 RETIRO ATM                       2,500.00               27,500.00",
                "05/05/2025 TRANSFERENCIA SPEI                          10,000.00   37,500.00",
                "07/05/2025 PAGO DE SERVICIOS                1,200.50               36,299.50",
                "10/05/2025 DEPOSITO CHEQUE                              3,500.75   39,800.25",
            ]
        },
        {
            "name": "inbursa_format_2.pdf", 
            "description": "Formato con fechas separadas por guiones",
            "content": [
                "INBURSA ESTADO DE CUENTA",
                "MAYO 2025",
                "IDE2001209V6",
                "",
                "02-05-2025 DEPOSITO EFECTIVO        5000.00        30000.00",
                "03-05-2025 RETIRO CAJERO           2500.00        27500.00", 
                "05-05-2025 TRANSFERENCIA SPEI     10000.00        37500.00",
                "07-05-2025 PAGO SERVICIOS          1200.50        36299.50",
                "10-05-2025 DEPOSITO CHEQUE         3500.75        39800.25",
            ]
        },
        {
            "name": "inbursa_format_3.pdf",
            "description": "Formato sin decimales y con espacios",
            "content": [
                "ESTADO CUENTA INBURSA",
                "MAYO 2025",
                "",
                "02 05 2025    DEPOSITO           5000        30000",
                "03 05 2025    RETIRO             2500        27500",
                "05 05 2025    TRANSFERENCIA     10000        37500", 
                "07 05 2025    PAGO               1200        36299",
                "10 05 2025    DEPOSITO           3500        39800",
            ]
        },
        {
            "name": "inbursa_format_4.pdf",
            "description": "Formato compacto con números seguidos",
            "content": [
                "INBURSA",
                "020525 DEPOSITO 5000.00 30000.00",
                "030525 RETIRO   2500.00 27500.00",
                "050525 TRANSF   10000.00 37500.00",
                "070525 PAGO     1200.50 36299.50",
                "100525 DEP      3500.75 39800.25",
            ]
        }
    ]
    
    created_files = []
    
    for format_test in test_formats:
        filename = format_test["name"]
        try:
            c = canvas.Canvas(filename, pagesize=letter)
            y_pos = 750
            
            c.drawString(50, y_pos, f"TEST: {format_test['description']}")
            y_pos -= 30
            
            for line in format_test["content"]:
                c.drawString(50, y_pos, line)
                y_pos -= 20
                if y_pos < 50:  # Nueva página si es necesario
                    c.showPage()
                    y_pos = 750
            
            c.save()
            created_files.append(filename)
            print(f"✅ Creado: {filename}")
            
        except Exception as e:
            print(f"❌ Error creando {filename}: {e}")
    
    return created_files

def test_all_formats():
    """Prueba todos los formatos creados"""
    
    print("🔍 PROBANDO DIFERENTES FORMATOS DE INBURSA")
    print("=" * 80)
    
    # Crear archivos de prueba
    print("📝 Creando archivos de prueba...")
    created_files = create_inbursa_format_tests()
    
    if not created_files:
        print("❌ No se pudieron crear archivos de prueba")
        return
    
    # Probar cada formato
    processor = PDFProcessor()
    
    for filename in created_files:
        print(f"\n🎯 PROBANDO: {filename}")
        print("-" * 50)
        
        try:
            with open(filename, 'rb') as f:
                pdf_bytes = f.read()
            
            resultado = processor.procesar_estado_cuenta(pdf_bytes, empresa_id=1)
            
            print(f"   ✅ Éxito: {resultado['exito']}")
            print(f"   🏦 Banco: {resultado.get('banco_detectado', 'No detectado')}")
            print(f"   📊 Movimientos: {resultado.get('total_movimientos', 0)}")
            print(f"   ⏱️ Tiempo: {resultado.get('tiempo_procesamiento', 0)}s")
            
            if resultado.get('movimientos'):
                print(f"   💰 Primeros movimientos:")
                for i, mov in enumerate(resultado['movimientos'][:3], 1):
                    fecha = mov.get('fecha', 'N/A')
                    concepto = mov.get('concepto', 'N/A')
                    monto = mov.get('monto', 'N/A')
                    print(f"      {i}. {fecha} - {concepto} - ${monto}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Limpiar archivo
        try:
            os.remove(filename)
        except:
            pass
    
    print(f"\n{'='*80}")
    print("🎯 PRUEBAS COMPLETADAS")

def test_aggressive_detection():
    """Prueba la detección agresiva con líneas específicas"""
    
    print("\n🔍 PROBANDO DETECCIÓN AGRESIVA DE LÍNEAS")
    print("=" * 60)
    
    # Líneas de prueba que podrían estar en un PDF de Inbursa
    test_lines = [
        "02/05/2025 DEPOSITO EN EFECTIVO 5,000.00 30,000.00",
        "03-05-2025 RETIRO ATM 2500.00 27500.00",
        "05 05 2025 TRANSFERENCIA SPEI 10000 37500",
        "070525 PAGO SERVICIOS 1200.50 36299.50",
        "10.05.2025 DEPOSITO CHEQUE 3500.75 39800.25",
        "2025/05/15 COMISION MANEJO 150.00 39650.25",
        "15 may 2025 TRANSFER RECIBIDA 8200 47850",
        "20250520 RETIRO VENTANILLA 5000 42850",
        "Mayo 15 DEPOSITO 1500.00 44350.00",
        "15/5/25 PAGO TARJETA 800 43550",
        # Líneas que NO deberían ser detectadas
        "GRUPO FINANCIERO INBURSA",
        "ESTADO DE CUENTA",
        "FECHA CONCEPTO CARGO ABONO SALDO",
        "================================",
        "CUENTA: 123456789",
        "PERIODO: 01/05/2025 AL 31/05/2025",
    ]
    
    processor = PDFProcessor()
    
    for i, linea in enumerate(test_lines, 1):
        es_movimiento = processor._es_linea_movimiento(linea)
        status = "✅ SÍ" if es_movimiento else "❌ NO"
        print(f"{i:2}. {status} | {linea}")
    
    print(f"\n🎯 Detección agresiva probada con {len(test_lines)} líneas")

def main():
    print("🚀 TEST COMPLETO DE FORMATOS INBURSA")
    print("=" * 80)
    
    # Probar detección agresiva
    test_aggressive_detection()
    
    # Probar diferentes formatos
    test_all_formats()
    
    print(f"\n💡 RECOMENDACIONES:")
    print("   1. Si ningún formato funciona, el PDF real usa otro formato")
    print("   2. Necesitaremos ver el contenido real del PDF")
    print("   3. Subir el PDF de nuevo para ver logs detallados")

if __name__ == "__main__":
    main()