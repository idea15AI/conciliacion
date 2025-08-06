#!/usr/bin/env python3
"""
Prueba el procesador mejorado con el PDF real del usuario
"""
import sys
import os
import logging

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.conciliacion.pdf_processor import PDFProcessor
from app.conciliacion.models import TipoBanco

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

def test_improved_processor():
    """Prueba el procesador mejorado"""
    print("🧪 Probando procesador mejorado...")
    
    # Crear instancia del procesador
    processor = PDFProcessor()
    
    # Texto de ejemplo del PDF del usuario
    texto_ejemplo = """
    CUENTA 50058959195 SUCURSAL PUEBLA PLAZA DORADA
    CLABE 036650500589591954 MONEDA MXN PESO MEXICANO
    PERIODO Del 01 May. 2025 al 31 May. 2025 FECHA DE CORTE 31 May. 2025
    31 GAT NO APLICA
    6.3051% RENDIMIENTOS 309.08
    5.8119%
    0.5000% COMISIONES EFECTIVAMENTE COBRADAS
    EN EL PERIODO 1,258.57
    FECHA REFERENCIA CONCEPTO CARGOS ABONOS SALDO
    MAY. 01 MAY. 02 3407784114 BALANCE INICIAL LIQUIDACION ADQUIRENTE CREDITO
    165.00 44,432.09
    44,597.09
    LIQUIDACION ADQ CREDITO-8993380
    MAY. 02 3407784117 TASA DE DESCTO CREDITO
    4.60 44,592.49
    APLICACION DE TASAS DE DESCUENTO-CREDITO-8993380
    MAY. 02 3407784117 IVA TASA DE DESCTO CREDITO
    0.74 44,591.75
    Tasa IVA 16.0 %
    MAY. 02 3407784123 LIQUIDACION ADQUIRENTE DEBITO
    1,050.00 45,641.75
    LIQUIDACION ADQ DEBITO-8993380
    MAY. 02 3407784128 TASA DE DESCTO DEBITO
    22.48 45,619.27
    APLICACION DE TASAS DE DESCUENTO-DEBITO-8993380
    MAY. 02 3407784128 IVA TASA DE DESCTO DEBITO
    3.60 45,615.67
    Tasa IVA 16.0 %
    MAY. 02 3408029858 DEPOSITO TEF
    472.46 46,088.13
    1041881046199 OPERADORA PAYPAL DE MEXICO S DE RL
    106
    MAY. 05 3411389231 LIQUIDACION ADQUIRENTE DEBITO
    1,115.00 47,203.13
    LIQUIDACION ADQ DEBITO-8993380
    """
    
    print("\n📋 Probando detección de líneas de movimiento...")
    
    # Probar la función _es_linea_movimiento
    lineas = texto_ejemplo.split('\n')
    
    for i, linea in enumerate(lineas):
        linea = linea.strip()
        if linea:
            es_movimiento = processor._es_linea_movimiento(linea)
            if es_movimiento:
                print(f"✅ Línea {i+1}: '{linea[:80]}...'")
            else:
                print(f"❌ Línea {i+1}: '{linea[:80]}...'")
    
    print("\n🔍 Probando parsing de líneas específicas...")
    
    # Líneas específicas del PDF del usuario
    lineas_ejemplo = [
        "MAY. 01 MAY. 02 3407784114 BALANCE INICIAL LIQUIDACION ADQUIRENTE CREDITO 165.00 44,432.09 44,597.09",
        "MAY. 02 3407784117 TASA DE DESCTO CREDITO 4.60 44,592.49",
        "MAY. 02 3407784117 IVA TASA DE DESCTO CREDITO 0.74 44,591.75",
        "MAY. 02 3407784123 LIQUIDACION ADQUIRENTE DEBITO 1,050.00 45,641.75",
        "MAY. 02 3407784128 TASA DE DESCTO DEBITO 22.48 45,619.27",
        "MAY. 02 3407784128 IVA TASA DE DESCTO DEBITO 3.60 45,615.67",
        "MAY. 02 3408029858 DEPOSITO TEF 472.46 46,088.13",
        "MAY. 05 3411389231 LIQUIDACION ADQUIRENTE DEBITO 1,115.00 47,203.13"
    ]
    
    for i, linea in enumerate(lineas_ejemplo):
        print(f"\n--- Línea {i+1} ---")
        print(f"Texto: {linea}")
        
        # Probar detección
        es_movimiento = processor._es_linea_movimiento(linea)
        print(f"¿Es movimiento? {es_movimiento}")
        
        if es_movimiento:
            # Probar parsing
            movimiento = processor._parsear_linea_bbva(linea, 1, 2025)
            if movimiento:
                print(f"✅ Movimiento extraído:")
                print(f"   Fecha: {movimiento.fecha}")
                print(f"   Concepto: {movimiento.concepto}")
                print(f"   Monto: ${movimiento.monto}")
                print(f"   Tipo: {movimiento.tipo.value}")
                print(f"   Referencia: {movimiento.referencia}")
            else:
                print("❌ No se pudo parsear el movimiento")
        else:
            print("❌ No se detectó como movimiento")
    
    print("\n✅ Prueba completada")

if __name__ == "__main__":
    test_improved_processor() 