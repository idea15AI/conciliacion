#!/usr/bin/env python3
"""
Prueba el PDFProcessor directamente con el PDF de prueba
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

def test_pdf_direct():
    """Prueba el PDFProcessor directamente"""
    print("🧪 Probando PDFProcessor directamente...")
    
    # Crear instancia del procesador
    processor = PDFProcessor()
    
    # Leer el PDF de prueba
    pdf_file = "test_real_format.pdf"
    if not os.path.exists(pdf_file):
        print(f"❌ Archivo no encontrado: {pdf_file}")
        return
    
    try:
        with open(pdf_file, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"📄 Archivo leído: {len(pdf_bytes)} bytes")
        
        # Procesar el PDF
        resultado = processor.procesar_estado_cuenta(pdf_bytes, empresa_id=1)
        
        print("✅ Resultado del procesamiento:")
        print(f"   Exito: {resultado.get('exito', False)}")
        print(f"   Banco detectado: {resultado.get('banco_detectado', 'N/A')}")
        print(f"   Total movimientos: {resultado.get('total_movimientos', 0)}")
        print(f"   Tiempo procesamiento: {resultado.get('tiempo_procesamiento', 0)}s")
        
        # Mostrar movimientos
        movimientos = resultado.get('movimientos', [])
        if movimientos:
            print(f"\n📋 Movimientos extraídos ({len(movimientos)}):")
            for i, mov in enumerate(movimientos[:5], 1):
                print(f"   {i}. {mov.get('fecha', 'N/A')} - {mov.get('concepto', 'N/A')} - ${mov.get('monto', 'N/A')} ({mov.get('tipo', 'N/A')})")
            if len(movimientos) > 5:
                print(f"   ... y {len(movimientos) - 5} movimientos más")
        else:
            print("❌ No se extrajeron movimientos")
        
        # Mostrar estadísticas
        stats = resultado.get('estadisticas', {})
        if stats:
            print(f"\n📊 Estadísticas:")
            print(f"   Movimientos extraídos: {stats.get('movimientos_extraidos', 0)}")
            print(f"   Movimientos validados: {stats.get('movimientos_validados', 0)}")
            print(f"   Movimientos únicos: {stats.get('movimientos_unicos', 0)}")
        
    except Exception as e:
        print(f"❌ Error en la prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_direct() 