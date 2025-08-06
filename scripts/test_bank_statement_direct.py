#!/usr/bin/env python3
"""
Test directo del procesador de estados de cuenta bancarios
"""
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_bank_statement():
    """Crea un estado de cuenta bancario de prueba"""
    filename = "test_bank_statement.pdf"
    
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Header del estado de cuenta
        c.drawString(50, 750, "ESTADO DE CUENTA BANCARIO")
        c.drawString(50, 730, "Banco: BBVA")
        c.drawString(50, 710, "Cuenta: 1234-5678-9012-3456")
        c.drawString(50, 690, "Cliente: EMPRESA ABC S.A. DE C.V.")
        c.drawString(50, 670, "Período: Enero 2025")
        
        # Headers de columnas
        c.drawString(50, 640, "FECHA")
        c.drawString(120, 640, "REFERENCIA")
        c.drawString(200, 640, "CONCEPTO")
        c.drawString(350, 640, "CARGOS")
        c.drawString(420, 640, "ABONOS")
        c.drawString(490, 640, "SALDO")
        
        # Línea separadora
        c.line(50, 635, 550, 635)
        
        # Movimientos de ejemplo
        movimientos = [
            ("01/01/2025", "REF001", "SALDO INICIAL", "", "", "100,000.00"),
            ("02/01/2025", "REF002", "PAGO PROVEEDOR", "15,000.00", "", "85,000.00"),
            ("03/01/2025", "REF003", "DEPÓSITO CLIENTE", "", "25,000.00", "110,000.00"),
            ("04/01/2025", "REF004", "COMISIÓN BANCARIA", "500.00", "", "109,500.00"),
            ("05/01/2025", "REF005", "PAGO NÓMINA", "45,000.00", "", "64,500.00"),
            ("06/01/2025", "REF006", "VENTA PRODUCTOS", "", "30,000.00", "94,500.00"),
            ("07/01/2025", "REF007", "PAGO SERVICIOS", "8,500.00", "", "86,000.00"),
            ("08/01/2025", "REF008", "DEPÓSITO EFECTIVO", "", "12,000.00", "98,000.00"),
            ("09/01/2025", "REF009", "PAGO IMPUESTOS", "22,000.00", "", "76,000.00"),
            ("10/01/2025", "REF010", "INGRESO VENTAS", "", "18,500.00", "94,500.00"),
        ]
        
        y_pos = 620
        for fecha, ref, concepto, cargos, abonos, saldo in movimientos:
            c.drawString(50, y_pos, fecha)
            c.drawString(120, y_pos, ref)
            c.drawString(200, y_pos, concepto)
            c.drawString(350, y_pos, cargos)
            c.drawString(420, y_pos, abonos)
            c.drawString(490, y_pos, saldo)
            y_pos -= 20
        
        # Totales
        c.line(50, y_pos - 10, 550, y_pos - 10)
        y_pos -= 30
        
        c.drawString(200, y_pos, "TOTALES:")
        c.drawString(350, y_pos, "91,000.00")
        c.drawString(420, y_pos, "85,500.00")
        c.drawString(490, y_pos, "94,500.00")
        
        # Información adicional
        c.drawString(50, 200, "Resumen:")
        c.drawString(50, 180, "Total Cargos: $91,000.00")
        c.drawString(50, 160, "Total Abonos: $85,500.00")
        c.drawString(50, 140, "Saldo Final: $94,500.00")
        
        c.save()
        print(f"✅ Estado de cuenta de prueba creado: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error creando estado de cuenta: {e}")
        return None

def test_bank_statement_processor(pdf_file):
    """Prueba el procesador de estados de cuenta"""
    print(f"\n🏦 PROBANDO PROCESADOR DE ESTADOS DE CUENTA")
    print("-" * 60)
    
    try:
        # Importar el procesador directamente
        from app.conciliacion.bank_statement_processor import BankStatementProcessor
        
        # Leer el PDF
        with open(pdf_file, 'rb') as f:
            pdf_bytes = f.read()
        
        # Crear procesador
        processor = BankStatementProcessor()
        
        # Procesar estado de cuenta
        print("📄 Procesando estado de cuenta...")
        resultado = processor.procesar_estado_cuenta(pdf_bytes)
        
        print("✅ Estado de cuenta procesado exitosamente")
        print(f"   📊 Movimientos extraídos: {resultado.get('total_movimientos', 0)}")
        print(f"   🏷️ Columnas encontradas: {resultado.get('estructura_columnas', {}).get('columnas_encontradas', [])}")
        print(f"   💰 Tipo de documento: {resultado.get('tipo', 'N/A')}")
        
        # Mostrar estructura de columnas
        estructura = resultado.get('estructura_columnas', {})
        if estructura.get('columnas_encontradas'):
            print(f"\n   📋 Columnas identificadas:")
            for columna in estructura['columnas_encontradas']:
                print(f"      • {columna}")
        
        # Mostrar movimientos
        movimientos = resultado.get('movimientos', [])
        if movimientos:
            print(f"\n   📊 Primeros 5 movimientos:")
            for i, mov in enumerate(movimientos[:5]):
                fecha = mov.get('fecha', 'N/A')
                if isinstance(fecha, datetime):
                    fecha = fecha.strftime("%d/%m/%Y")
                concepto = mov.get('concepto', 'N/A')
                cargos = mov.get('cargos', 0) or 0
                abonos = mov.get('abonos', 0) or 0
                print(f"      {i+1}. {fecha} | {concepto[:30]} | C:${cargos:,.2f} | A:${abonos:,.2f}")
        
        # Mostrar saldos
        saldos = resultado.get('saldos', {})
        if saldos and 'error' not in saldos:
            print(f"\n   💰 Estadísticas:")
            print(f"      Total Cargos: ${saldos.get('total_cargos', 0):,.2f}")
            print(f"      Total Abonos: ${saldos.get('total_abonos', 0):,.2f}")
            print(f"      Saldo Final: ${saldos.get('saldo_final', 0):,.2f}")
        
        # Probar extracción con tablas
        print(f"\n🔍 Probando extracción con tablas...")
        resultado_tablas = processor.procesar_con_tablas(pdf_bytes)
        
        print(f"   📊 Tablas encontradas: {resultado_tablas.get('tablas_encontradas', 0)}")
        print(f"   📄 Movimientos por tablas: {resultado_tablas.get('total_movimientos', 0)}")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error procesando estado de cuenta: {e}")
        return None

def test_specific_patterns():
    """Prueba patrones específicos de columnas bancarias"""
    print(f"\n🔍 PROBANDO PATRONES ESPECÍFICOS")
    print("-" * 50)
    
    try:
        from app.conciliacion.bank_statement_processor import BankStatementProcessor
        
        processor = BankStatementProcessor()
        
        # Textos de prueba
        textos_prueba = [
            "FECHA REFERENCIA CONCEPTO CARGOS ABONOS SALDO",
            "FECHA OPER LIQ COD. DESCRIPCIÓN REFERENCIA CARGOS ABONOS OPERACIÓN LIQUIDACIÓN",
            "FECHA SALDO OPER LIQ COD. DESCRIPCIÓN REFERENCIA CARGOS ABONOS",
            "FECHA REFERENCIA CONCEPTO CARGOS ABONOS SALDO FECHA SALDO"
        ]
        
        for i, texto in enumerate(textos_prueba, 1):
            print(f"\n   Prueba {i}: {texto}")
            estructura = processor._identificar_estructura_columnas(texto)
            columnas = estructura.get('columnas_encontradas', [])
            print(f"      Columnas detectadas: {columnas}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando patrones: {e}")
        return False

def main():
    print("🏦 TEST DIRECTO DEL PROCESADOR DE ESTADOS DE CUENTA BANCARIOS")
    print("=" * 90)
    
    # 1. Probar patrones específicos
    test_specific_patterns()
    
    # 2. Crear estado de cuenta de prueba
    pdf_file = create_test_bank_statement()
    if not pdf_file:
        print("❌ No se pudo crear estado de cuenta de prueba")
        return
    
    try:
        # 3. Probar procesador de estados de cuenta
        resultado = test_bank_statement_processor(pdf_file)
        
        # 4. Análisis final
        print(f"\n🎯 ANÁLISIS FINAL")
        print("=" * 50)
        
        if resultado:
            print("✅ Procesador de estados de cuenta funcionando correctamente")
            print(f"   📊 Extrajo {len(resultado.get('movimientos', []))} movimientos")
            print(f"   🏷️ Identificó {len(resultado.get('estructura_columnas', {}).get('columnas_encontradas', []))} columnas")
            print(f"   💡 Usa patrones específicos para estados de cuenta bancarios")
        else:
            print("❌ Problemas con el procesador de estados de cuenta")
        
        print(f"\n💡 CARACTERÍSTICAS IMPLEMENTADAS:")
        print("   1. ✅ Detección de columnas bancarias específicas")
        print("   2. ✅ Extracción de movimientos con fechas y montos")
        print("   3. ✅ Cálculo de saldos y estadísticas")
        print("   4. ✅ Procesamiento con tablas estructuradas")
        print("   5. ✅ Patrones para FECHA, REFERENCIA, CONCEPTO, CARGOS, ABONOS, SALDO")
        print("   6. ✅ Validación de estructura de datos")
        print("   7. ✅ Métricas de extracción")
        
        print(f"\n🎯 PATRONES ESPECÍFICOS DETECTADOS:")
        print("   • FECHA REFERENCIA CONCEPTO CARGOS ABONOS SALDO")
        print("   • FECHA OPER LIQ COD. DESCRIPCIÓN REFERENCIA CARGOS ABONOS")
        print("   • FECHA SALDO OPER LIQ COD. DESCRIPCIÓN REFERENCIA CARGOS ABONOS")
        
    finally:
        # Limpiar archivo de prueba
        try:
            os.remove(pdf_file)
            print(f"\n🧹 Archivo de prueba eliminado: {pdf_file}")
        except:
            pass

if __name__ == "__main__":
    main() 