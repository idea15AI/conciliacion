#!/usr/bin/env python3
"""
Script para probar el formato real de BANORTE basado en la imagen proporcionada
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

def crear_pdf_banorte_real():
    """Crea un PDF con el formato real de BANORTE basado en la imagen."""
    filename = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "DETALLE DE MOVIMIENTOS (PESOS)")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 730, "Enlace Negocios Basica")
    
    # Encabezados
    c.setFont("Helvetica-Bold", 10)
    headers = ["FECHA", "DESCRIPCIÓN/ESTABLECIMIENTO", "MONTO DEL DEPOSITO", "MONTO DEL RETIRO", "SALDO"]
    y = 700
    
    for i, header in enumerate(headers):
        x = 50 + i * 90
        c.drawString(x, y, header)
    
    # Datos reales de BANORTE
    c.setFont("Helvetica", 8)
    data = [
        ["31-DIC-22", "SALDO ANTERIOR", "", "", "1,190,950.98"],
        ["03-ENE-23", "DEPOSITO DE CUENTA DE TERCEROS 0000000655 DE LA CUENTA 0557374517 PAGO FACT 655 RENTA JUAREZ ENERO 2023", "197,200.00", "", "1,388,150.98"],
        ["03-ENE-23", "085902932284300331 SPEI RECIBIDO, BCO:0002 BANAMEX HR LIQ: 14:54:24 DEL CLIENTE NATALY MORALES HERNANDEZ DE LA CLABE 002650700555078387 CON RFC MOHN850126221 CONCEPTO: Transferencia interbancaria REFERENCIA: 0030123 CVE RAST: 085902932284300331", "11,658.00", "", "1,399,808.98"],
        ["04-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000040123 IVA:00000000.00, A LA CUENTA: 0593419658 AL R.F.C. CAGX310110DX1", "", "110,254.00", "1,289,554.98"],
        ["04-ENE-23", "COMPRA ORDEN DE PAGO SPEI 0040123-REFERENCIA CTA/CLABE: 036650500106145550, BEM SPEI BCO:036 BENEF:ALMA LIDIA DIB QUEZAD (DATO NO VERIF POR ESTA INST), Transferencia CVE RASTREO: 8846APR1202301042072483137 RFC: DQA8903033L5 IVA: 000000000000.00 INBURSA HORA LIQ: 12:31:05", "", "70,000.00", "1,219,554.98"],
        ["04-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000040123 IVA:00000000.00, A LA CUENTA: 0444407092 AL R.F.C. ECP961210MN3", "", "124,453.00", "1,095,101.98"],
        ["05-ENE-23", "2023010640014BMOV0000477987640 SPEI RECIBIDO, BCO:0014 SANTANDER HR LIQ: 20:03:18 DEL CLIENTE LESSLY GABRIELA BRETON MURO DE LA CLABE 014650250045506027 CON RFC BEML950410FZ4 CONCEPTO: RENTA ENERO REFERENCIA: 7479461 CVE RAST: 2023010640014BMOV0000477987640", "7,540.00", "", "1,102,641.98"],
        ["11-ENE-23", "CUENTAS POR PAGAR-SAP 0001072097 000000662023REPP", "437,359.86", "", "1,540,001.84"],
        ["12-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000120123 IVA:00000000.00, A LA CUENTA: 0444407261 AL R.F.C. GIA160822GY9", "", "160,593.00", "1,379,408.84"],
        ["12-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000120123 IVA:00000000.00, A LA CUENTA: 0444407038 AL R.F.C. ECP961210MN3", "", "120,593.00", "1,258,815.84"],
        ["12-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000120123 IVA:00000000.00, A LA CUENTA: 0450578630 AL R.F.C. GIJ150410HC7", "", "120,593.00", "1,138,222.84"],
        ["12-ENE-23", "COMPRA ORDEN DE PAGO SPEI 0120123-REFERENCIA CTA/CLABE: 002650039314488960, BEM SPEI BCO:002 BENEF:Despacho Manuel Flores y Asocia (DATO NO VERIF POR ESTA INST), pago contabilidad Enero 2023 CVE RASTREO: 8846APR2202301122084169015 RFC: DMF950118409 IVA: 000000000000.00 BANAMEX HORA LIQ: 11:43:14", "", "3,356.81", "1,134,866.03"],
        ["15-ENE-23", "036APPM15012023107434731 SPEI RECIBIDO, BCO:0036 INBURSA HR LIQ: 09:32:07 DEL CLIENTE MARISA LOPEZ FERNANDEZ DE LA CLABE 036669500469694771 CON RFC LOFM89062561A CONCEPTO: renta enero 2023 REFERENCIA: 0000001 CVE RAST: 036APPM15012023107434731", "15,544.00", "", "1,150,410.03"],
        ["17-ENE-23", "50110739TRANSBP171830677 SPEI RECIBIDO, BCO:0137 BANCOPPEL HR LIQ: 16:20:47 DEL CLIENTE SILVIANO LOPEZ MONTIEL DE LA CLABE 137650101050420739 CON RFC LOMS761103665 CONCEPTO: pago de renta REFERENCIA: 7183067 CVE RAST: 50110739TRANSBP171830677", "6,430.00", "", "1,156,840.03"],
        ["24-ENE-23", "2023012440014 BET0000434268030 SPEI RECIBIDO, BCO:0014 SANTANDER HR LIQ: 13:28:21 DEL", "104,310.84", "", "1,261,150.87"]
    ]
    
    y = 650
    for row in data:
        for i, cell in enumerate(row):
            x = 50 + i * 90
            # Truncar texto muy largo para que quepa en la página
            if len(cell) > 20:
                cell = cell[:17] + "..."
            c.drawString(x, y, cell)
        y -= 15
    
    c.save()
    return filename

def probar_banorte_real():
    """Prueba el formato real de BANORTE."""
    print(f"\n🏦 Probando BANORTE: Formato Real")
    print("=" * 60)
    
    try:
        # Crear PDF de prueba
        pdf_path = crear_pdf_banorte_real()
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
                
                # Verificar casos específicos de BANORTE
                if "DEPOSITO DE CUENTA DE TERCEROS" in concepto.upper():
                    if tipo == "abono":
                        print(f"    ✅ CORRECTO: DEPOSITO DE CUENTA DE TERCEROS detectado como ABONO")
                    else:
                        print(f"    ❌ INCORRECTO: DEPOSITO DE CUENTA DE TERCEROS detectado como {tipo.upper()}")
                
                if "TRASPASO A CUENTA DE TERCEROS" in concepto.upper():
                    if tipo == "cargo":
                        print(f"    ✅ CORRECTO: TRASPASO A CUENTA DE TERCEROS detectado como CARGO")
                    else:
                        print(f"    ❌ INCORRECTO: TRASPASO A CUENTA DE TERCEROS detectado como {tipo.upper()}")
                
                if "SPEI RECIBIDO" in concepto.upper():
                    if tipo == "abono":
                        print(f"    ✅ CORRECTO: SPEI RECIBIDO detectado como ABONO")
                    else:
                        print(f"    ❌ INCORRECTO: SPEI RECIBIDO detectado como {tipo.upper()}")
                
                if "COMPRA ORDEN DE PAGO SPEI" in concepto.upper():
                    if tipo == "cargo":
                        print(f"    ✅ CORRECTO: COMPRA ORDEN DE PAGO SPEI detectado como CARGO")
                    else:
                        print(f"    ❌ INCORRECTO: COMPRA ORDEN DE PAGO SPEI detectado como {tipo.upper()}")
                
                if "CUENTAS POR PAGAR-SAP" in concepto.upper():
                    if tipo == "abono":
                        print(f"    ✅ CORRECTO: CUENTAS POR PAGAR-SAP detectado como ABONO")
                    else:
                        print(f"    ❌ INCORRECTO: CUENTAS POR PAGAR-SAP detectado como {tipo.upper()}")
                
        else:
            print(f"❌ Error: {resultado.get('error', 'Error desconocido')}")
            
    except Exception as e:
        print(f"❌ Error procesando formato real de BANORTE: {e}")
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
    print("🧪 Test de Formato Real de BANORTE con Gemini")
    print("=" * 60)
    
    # Verificar configuración
    try:
        processor = GeminiProcessor()
        print("✅ Configuración de Gemini verificada")
    except Exception as e:
        print(f"❌ Error de configuración: {e}")
        return
    
    # Probar formato real de BANORTE
    probar_banorte_real()
    
    print("\n" + "=" * 60)
    print("🎉 ¡Test de formato real de BANORTE completado!")

if __name__ == "__main__":
    main() 