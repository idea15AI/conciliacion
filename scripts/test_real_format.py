#!/usr/bin/env python3
"""
Script para probar el PDFProcessor con el formato real del usuario
"""

import os
import sys
import json
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_real_format():
    """Prueba el procesador con el formato real del usuario"""
    
    print("🧪 Probando con formato real del usuario...")
    
    # Datos de ejemplo basados en el formato real
    datos_reales = [
        {
            'fecha': 'MAY. 01',
            'referencia': '3407784114',
            'concepto': 'BALANCE INICIAL LIQUIDACION ADQUIRENTE CREDITO',
            'abono': '165.00',
            'saldo': '44,432.09'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '3407784117',
            'concepto': 'TASA DE DESCTO CREDITO',
            'abono': '4.60',
            'saldo': '44,592.49'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '3407784117',
            'concepto': 'IVA TASA DE DESCTO CREDITO',
            'abono': '0.74',
            'saldo': '44,591.75'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '3407784123',
            'concepto': 'LIQUIDACION ADQUIRENTE DEBITO',
            'cargo': '1,050.00',
            'saldo': '45,641.75'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '3407784128',
            'concepto': 'TASA DE DESCTO DEBITO',
            'cargo': '22.48',
            'saldo': '45,619.27'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '3407784128',
            'concepto': 'IVA TASA DE DESCTO DEBITO',
            'cargo': '3.60',
            'saldo': '45,615.67'
        },
        {
            'fecha': 'MAY. 02',
            'referencia': '3408029858',
            'concepto': 'DEPOSITO TEF',
            'abono': '472.46',
            'saldo': '46,088.13'
        },
        {
            'fecha': 'MAY. 05',
            'referencia': '3411389231',
            'concepto': 'LIQUIDACION ADQUIRENTE DEBITO',
            'cargo': '1,115.00',
            'saldo': '47,203.13'
        }
    ]
    
    try:
        # Importar y usar el procesador
        from app.conciliacion.pdf_processor import PDFProcessor, MovimientoBancario, TipoMovimiento
        from datetime import date
        from decimal import Decimal
        
        processor = PDFProcessor()
        
        # Simular el procesamiento de los datos reales
        movimientos = []
        
        for i, dato in enumerate(datos_reales, 1):
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
                
                # Crear movimiento
                movimiento = MovimientoBancario(
                    fecha=fecha,
                    concepto=dato['concepto'],
                    monto=monto,
                    tipo=tipo,
                    referencia=dato.get('referencia'),
                    saldo=processor.amount_parser.parse_amount(dato.get('saldo', '')),
                    pagina_origen=1
                )
                
                movimientos.append(movimiento)
                print(f"✅ Movimiento {i}: {movimiento.fecha} - {movimiento.concepto} - ${movimiento.monto} ({tipo.value})")
                
            except Exception as e:
                print(f"❌ Error procesando movimiento {i}: {str(e)}")
                continue
        
        print(f"\n📊 Resultados:")
        print(f"   Total movimientos procesados: {len(movimientos)}")
        print(f"   Abonos: {len([m for m in movimientos if m.tipo == TipoMovimiento.ABONO])}")
        print(f"   Cargos: {len([m for m in movimientos if m.tipo == TipoMovimiento.CARGO])}")
        
        # Guardar resultados
        resultado = {
            'exito': True,
            'banco_detectado': 'bbva',
            'total_movimientos': len(movimientos),
            'tiempo_procesamiento': 0.0,
            'movimientos': [m.to_dict() for m in movimientos]
        }
        
        with open('resultados_formato_real.json', 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: resultados_formato_real.json")
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_format() 