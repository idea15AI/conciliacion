#!/usr/bin/env python3
"""
Test completo del sistema híbrido avanzado
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

def get_first_company_rfc():
    """Obtiene el RFC de la primera empresa"""
    try:
        response = requests.get(f"{API_BASE}/conciliacion/empresas")
        if response.status_code == 200:
            empresas = response.json()
            if empresas:
                rfc = empresas[0]['rfc']
                print(f"📊 Usando empresa: {rfc}")
                return rfc
            else:
                print("⚠️ No hay empresas registradas")
                return None
        else:
            print(f"❌ Error obteniendo empresas: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def create_test_pdf_complex():
    """Crea un PDF de prueba complejo para probar el sistema híbrido"""
    filename = "test_hibrido_complejo.pdf"
    
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Página 1: Información del banco y resumen
        c.drawString(50, 750, "GRUPO FINANCIERO INBURSA")
        c.drawString(50, 730, "ESTADO DE CUENTA EMPRESARIAL")
        c.drawString(50, 710, "PERIODO: 01/05/2025 AL 31/05/2025")
        c.drawString(50, 690, "CUENTA: 123456789-01")
        c.drawString(50, 670, "RFC: IDE2001209V6")
        
        # Resumen de saldos
        c.drawString(50, 630, "RESUMEN DEL PERIODO:")
        c.drawString(50, 610, "Saldo Inicial: $44,432.09")
        c.drawString(50, 590, "Total Depósitos: $30,955.76")
        c.drawString(50, 570, "Total Retiros: $1,282.74")
        c.drawString(50, 550, "Saldo Final: $74,105.11")
        
        # Nueva página para movimientos
        c.showPage()
        
        # Página 2: Movimientos detallados
        c.drawString(50, 750, "DETALLE DE MOVIMIENTOS")
        c.drawString(50, 730, "=" * 70)
        
        # Header de tabla
        c.drawString(50, 700, "FECHA      CONCEPTO                              CARGO      ABONO      SALDO")
        c.drawString(50, 685, "-" * 85)
        
        # Movimientos complejos con diferentes formatos
        movimientos_complejos = [
            "02/05/2025 DEPOSITO EN EFECTIVO SUCURSAL 001                  5,000.00   49,432.09",
            "03/05/2025 TRF SPEI RECIBIDA REF:12345                      10,000.00   59,432.09",
            "04/05/2025 PAGO NOMINA LOTE:NOM001           15,000.00                   44,432.09",
            "05/05/2025 COMISION POR TRANSFERENCIA             12.50                   44,419.59",
            "08/05/2025 DEP CHEQUE BCO EXTERNO #789456                    8,500.25   52,919.84",
            "10/05/2025 PAGO PROVEEDORES LOTE:PROV25       7,850.00                   45,069.84",
            "12/05/2025 INTERES GANADO CUENTA                               125.50   45,195.34",
            "15/05/2025 RETIRO ATM SUCURSAL 105               500.00                   44,695.34",
            "18/05/2025 TRF SPEI ENVIADA REF:67890          2,200.00                   42,495.34",
            "20/05/2025 DEPOSITO VENTANILLA SUC 002                       3,750.00   46,245.34",
            "22/05/2025 PAGO SERVICIOS DOMICILIADO            285.75                   45,959.59",
            "25/05/2025 TRF INTERBANCARIA RECIBIDA                       12,500.00   58,459.59",
            "28/05/2025 COMISION MANEJO CUENTA                 45.00                   58,414.59",
            "30/05/2025 DEPOSITO CHEQUE MISMO BANCO                       8,250.75   66,665.34",
            "31/05/2025 AJUSTE SALDO POR INTERES                            439.77   67,105.11"
        ]
        
        y_pos = 665
        for movimiento in movimientos_complejos:
            c.drawString(50, y_pos, movimiento)
            y_pos -= 18
            
            if y_pos < 100:  # Nueva página si es necesario
                c.showPage()
                y_pos = 750
        
        # Página 3: Información adicional y notas
        c.showPage()
        c.drawString(50, 750, "INFORMACIÓN ADICIONAL")
        c.drawString(50, 730, "Comisiones del período: $1,342.25")
        c.drawString(50, 710, "Intereses ganados: $565.27")
        c.drawString(50, 690, "Número de movimientos: 15")
        c.drawString(50, 670, "Días con actividad: 12")
        
        # Agregar texto con formato complejo para probar la extracción
        c.drawString(50, 630, "NOTAS:")
        c.drawString(50, 610, "- Cuenta con seguro IPAB hasta $400,000 UDIS")
        c.drawString(50, 590, "- Horario de atención: L-V 8:30-17:30")
        c.drawString(50, 570, "- Teléfono: 55-5447-8000")
        
        c.save()
        print(f"✅ PDF complejo creado: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error creando PDF: {e}")
        return None

def test_hybrid_endpoint(rfc_empresa, pdf_file):
    """Prueba el endpoint híbrido"""
    print(f"\n🚀 PROBANDO ENDPOINT HÍBRIDO")
    print("-" * 50)
    
    try:
        with open(pdf_file, 'rb') as f:
            files = {'file': (pdf_file, f, 'application/pdf')}
            
            response = requests.post(
                f"{API_BASE}/conciliacion/subir-estado-cuenta-hibrido?rfc_empresa={rfc_empresa}",
                files=files,
                timeout=120  # Más tiempo para el procesamiento híbrido
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ ÉXITO - Procesamiento híbrido completado")
                print(f"   🏦 Banco: {data.get('banco_detectado', 'N/A')}")
                print(f"   📊 Movimientos: {data.get('total_movimientos_extraidos', 0)}")
                print(f"   ⏱️ Tiempo: {data.get('tiempo_procesamiento_segundos', 0)}s")
                print(f"   💬 Mensaje: {data.get('mensaje', 'N/A')}")
                
                # Mostrar detalles del procesamiento híbrido
                mensaje = data.get('mensaje', '')
                if 'método:' in mensaje:
                    metodo_usado = mensaje.split('método:')[1].split(',')[0].strip()
                    print(f"   🔧 Método usado: {metodo_usado}")
                
                if 'confianza:' in mensaje:
                    confianza = mensaje.split('confianza:')[1].split(')')[0].strip()
                    print(f"   📈 Confianza: {confianza}")
                
                # Mostrar primeros movimientos
                if data.get('movimientos_extraidos'):
                    print(f"\n   💰 Primeros movimientos extraídos:")
                    for i, mov in enumerate(data['movimientos_extraidos'][:5], 1):
                        fecha = mov.get('fecha', 'N/A')
                        concepto = mov.get('concepto', 'N/A')[:40] + '...' if len(mov.get('concepto', '')) > 40 else mov.get('concepto', 'N/A')
                        monto = mov.get('monto', 0)
                        tipo = mov.get('tipo', 'N/A')
                        print(f"      {i}. {fecha} | {concepto} | ${monto:,.2f} | {tipo}")
                
                return data
            else:
                print(f"❌ Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Detalle: {error_data.get('detail', 'Sin detalles')}")
                except:
                    print(f"   Respuesta: {response.text}")
                return None
                
    except requests.exceptions.Timeout:
        print("❌ Timeout - El procesamiento tomó demasiado tiempo")
        return None
    except Exception as e:
        print(f"❌ Error en la petición: {e}")
        return None

def compare_methods(rfc_empresa, pdf_file):
    """Compara los tres métodos disponibles"""
    print(f"\n📊 COMPARACIÓN DE MÉTODOS")
    print("=" * 60)
    
    endpoints = {
        "Local": "conciliacion/subir-estado-cuenta",
        "OpenAI": "conciliacion/subir-estado-cuenta-openai", 
        "Híbrido": "conciliacion/subir-estado-cuenta-hibrido"
    }
    
    resultados = {}
    
    for nombre, endpoint in endpoints.items():
        print(f"\n🧪 Probando método: {nombre}")
        try:
            with open(pdf_file, 'rb') as f:
                files = {'file': (pdf_file, f, 'application/pdf')}
                
                response = requests.post(
                    f"{API_BASE}/{endpoint}?rfc_empresa={rfc_empresa}",
                    files=files,
                    timeout=90
                )
                
                if response.status_code == 200:
                    data = response.json()
                    resultados[nombre] = {
                        "movimientos": data.get('total_movimientos_extraidos', 0),
                        "tiempo": data.get('tiempo_procesamiento_segundos', 0),
                        "banco": data.get('banco_detectado', 'N/A'),
                        "exito": True
                    }
                    print(f"   ✅ {data.get('total_movimientos_extraidos', 0)} movimientos en {data.get('tiempo_procesamiento_segundos', 0)}s")
                else:
                    resultados[nombre] = {"exito": False, "error": response.status_code}
                    print(f"   ❌ Error: {response.status_code}")
                    
        except Exception as e:
            resultados[nombre] = {"exito": False, "error": str(e)}
            print(f"   ❌ Error: {e}")
    
    # Mostrar comparación final
    print(f"\n📊 RESUMEN DE COMPARACIÓN")
    print("-" * 40)
    for metodo, resultado in resultados.items():
        if resultado.get("exito"):
            print(f"{metodo:8}: {resultado['movimientos']:3} movimientos | {resultado['tiempo']:4}s")
        else:
            print(f"{metodo:8}: ❌ Error - {resultado.get('error', 'Desconocido')}")
    
    return resultados

def main():
    print("🚀 TEST COMPLETO DEL SISTEMA HÍBRIDO AVANZADO")
    print("=" * 80)
    
    # 1. Verificar servidor
    if not check_server_status():
        print("❌ No se puede continuar sin servidor")
        return
    
    # 2. Obtener empresa
    rfc_empresa = get_first_company_rfc()
    if not rfc_empresa:
        print("❌ No se puede continuar sin empresa")
        return
    
    # 3. Crear PDF de prueba complejo
    pdf_file = create_test_pdf_complex()
    if not pdf_file:
        print("❌ No se pudo crear PDF de prueba")
        return
    
    try:
        # 4. Probar endpoint híbrido específicamente
        resultado_hibrido = test_hybrid_endpoint(rfc_empresa, pdf_file)
        
        # 5. Comparar todos los métodos
        resultados_comparacion = compare_methods(rfc_empresa, pdf_file)
        
        # 6. Análisis final
        print(f"\n🎯 ANÁLISIS FINAL")
        print("=" * 40)
        
        if resultado_hibrido:
            print("✅ Sistema híbrido funcionando correctamente")
            print(f"   📊 Extrajo {resultado_hibrido.get('total_movimientos_extraidos', 0)} movimientos")
            print(f"   💡 El sistema híbrido combina múltiples técnicas para máxima precisión")
        else:
            print("❌ Problemas con el sistema híbrido")
        
        print(f"\n💡 RECOMENDACIONES:")
        print("   1. El método híbrido debería ser el más completo")
        print("   2. Combina velocidad local con precisión de IA")
        print("   3. Se activa automáticamente según la complejidad")
        
    finally:
        # Limpiar archivo de prueba
        try:
            os.remove(pdf_file)
            print(f"\n🧹 Archivo de prueba eliminado: {pdf_file}")
        except:
            pass

if __name__ == "__main__":
    main()