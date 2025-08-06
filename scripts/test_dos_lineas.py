#!/usr/bin/env python3
"""
Script para probar el procesamiento de conceptos de dos líneas
"""

import os
import sys
import json
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_conceptos_dos_lineas():
    """Prueba el procesamiento de conceptos de dos líneas"""
    
    print("🧪 Probando conceptos de dos líneas...")
    
    # Datos de ejemplo con conceptos de dos líneas
    datos_dos_lineas = [
        {
            'fecha': 'MAY. 01',
            'referencia': '3407784114',
            'concepto': 'BALANCE INICIAL\nLIQUIDACION ADQUIRENTE CREDITO',
            'abono': '165.00',
            'saldo': '44,432.09'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '',  # Sin referencia en primera línea
            'concepto': 'TASA DE DESCTO CREDITO\nAPLICACION DE TASAS DE DESCUENTO-CREDITO-8993380',
            'abono': '4.60',
            'saldo': '44,592.49'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '3407784117',  # Referencia en segunda línea
            'concepto': 'IVA TASA DE DESCTO CREDITO\nTasa IVA 16.0 %',
            'abono': '0.74',
            'saldo': '44,591.75'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '3407784123',
            'concepto': 'LIQUIDACION ADQUIRENTE DEBITO\nLIQUIDACION ADQ DEBITO-8993380',
            'cargo': '1,050.00',
            'saldo': '45,641.75'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '',  # Sin referencia
            'concepto': 'DEPOSITO TEF\n1041881046199 OPERADORA PAYPAL DE MEXICO S DE RL\n106',
            'abono': '472.46',
            'saldo': '46,088.13'
        }
    ]
    
    try:
        # Importar y usar el procesador
        from app.conciliacion.pdf_processor import PDFProcessor, MovimientoBancario, TipoMovimiento
        from datetime import date
        from decimal import Decimal
        
        processor = PDFProcessor()
        
        # Simular el procesamiento de los datos de dos líneas
        movimientos = []
        
        for i, dato in enumerate(datos_dos_lineas, 1):
            try:
                # Parsear fecha
                fecha = processor.date_parser.parse_date(dato['fecha'], 2025)
                if not fecha:
                    print(f"❌ Error parseando fecha: {dato['fecha']}")
                    continue
                
                # Parsear monto
                monto = None
                tipo = None
                
                if 'cargo' in dato and dato['cargo']:
                    monto = processor.amount_parser.parse_amount(dato['cargo'])
                    tipo = TipoMovimiento.CARGO
                elif 'abono' in dato and dato['abono']:
                    monto = processor.amount_parser.parse_amount(dato['abono'])
                    tipo = TipoMovimiento.ABONO
                
                if not monto:
                    print(f"❌ Error parseando monto para movimiento {i}")
                    continue
                
                # Procesar concepto de dos líneas
                concepto_original = dato['concepto']
                concepto_consolidado = processor._consolidar_concepto_dos_lineas(concepto_original)
                
                print(f"📝 Concepto original: '{concepto_original}'")
                print(f"📝 Concepto consolidado: '{concepto_consolidado}'")
                
                # Crear movimiento
                movimiento = MovimientoBancario(
                    fecha=fecha,
                    concepto=concepto_consolidado,
                    monto=monto,
                    tipo=tipo,
                    referencia=dato.get('referencia') if dato.get('referencia') else None,
                    saldo=processor.amount_parser.parse_amount(dato.get('saldo', '')),
                    pagina_origen=1
                )
                
                movimientos.append(movimiento)
                print(f"✅ Movimiento {i}: {movimiento.fecha} - {movimiento.concepto} - ${movimiento.monto} ({tipo.value})")
                if movimiento.referencia:
                    print(f"   📋 Referencia: {movimiento.referencia}")
                else:
                    print(f"   📋 Sin referencia")
                print()
                
            except Exception as e:
                print(f"❌ Error procesando movimiento {i}: {str(e)}")
                continue
        
        print(f"\n📊 Resultados:")
        print(f"   Total movimientos procesados: {len(movimientos)}")
        print(f"   Abonos: {len([m for m in movimientos if m.tipo == TipoMovimiento.ABONO])}")
        print(f"   Cargos: {len([m for m in movimientos if m.tipo == TipoMovimiento.CARGO])}")
        print(f"   Con referencia: {len([m for m in movimientos if m.referencia])}")
        print(f"   Sin referencia: {len([m for m in movimientos if not m.referencia])}")
        
        # Guardar resultados
        resultado = {
            'exito': True,
            'banco_detectado': 'bbva',
            'total_movimientos': len(movimientos),
            'tiempo_procesamiento': 0.0,
            'movimientos': [m.to_dict() for m in movimientos]
        }
        
        with open('resultados_dos_lineas.json', 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: resultados_dos_lineas.json")
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_conceptos_dos_lineas() 