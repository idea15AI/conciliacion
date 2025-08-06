#!/usr/bin/env python3
"""
Script para capturar logs detallados del servidor durante el procesamiento
"""
import logging
import sys
import os

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.pdf_processor import PDFProcessor
from app.conciliacion.models import TipoBanco

def test_con_pdf_ejemplo():
    """Crea un PDF de ejemplo para probar la extracción"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        print("📝 Creando PDF de ejemplo con movimientos de Inbursa...")
        
        # Crear PDF de prueba
        filename = "test_inbursa_movimientos.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Header del banco
        c.drawString(50, 750, "GRUPO FINANCIERO INBURSA")
        c.drawString(50, 730, "ESTADO DE CUENTA")
        c.drawString(50, 710, "PERIODO: 01/05/2025 AL 31/05/2025")
        c.drawString(50, 690, "CUENTA: 123456789")
        
        # Header de la tabla
        c.drawString(50, 650, "FECHA         CONCEPTO                           CARGO        ABONO       SALDO")
        c.drawString(50, 630, "===============================================================================")
        
        # Movimientos de ejemplo
        movimientos = [
            "01/05/2025    SALDO INICIAL                                               25,000.00",
            "02/05/2025    DEPOSITO EN EFECTIVO           5,000.00                   30,000.00",
            "03/05/2025    RETIRO ATM                                  2,500.00      27,500.00",
            "05/05/2025    TRANSFERENCIA SPEI             10,000.00                  37,500.00",
            "07/05/2025    PAGO SERVICIOS                              1,200.50      36,299.50",
            "10/05/2025    DEPOSITO CHEQUE                3,500.75                   39,800.25",
            "15/05/2025    COMISION MANEJO                             150.00        39,650.25",
            "20/05/2025    TRANSFERENCIA RECIBIDA         8,200.00                   47,850.25",
            "25/05/2025    RETIRO VENTANILLA                           5,000.00      42,850.25",
            "31/05/2025    SALDO FINAL                                               42,850.25"
        ]
        
        y_pos = 610
        for movimiento in movimientos:
            c.drawString(50, y_pos, movimiento)
            y_pos -= 20
        
        c.save()
        print(f"✅ PDF creado: {filename}")
        
        # Ahora procesarlo
        print("\n🤖 Procesando con PDFProcessor...")
        
        with open(filename, 'rb') as f:
            pdf_bytes = f.read()
        
        processor = PDFProcessor()
        resultado = processor.procesar_estado_cuenta(pdf_bytes, empresa_id=1)
        
        print(f"\n📊 RESULTADOS:")
        print(f"   Éxito: {resultado['exito']}")
        print(f"   Banco: {resultado.get('banco_detectado', 'No detectado')}")
        print(f"   Movimientos: {resultado.get('total_movimientos', 0)}")
        print(f"   Tiempo: {resultado.get('tiempo_procesamiento', 0)}s")
        
        if resultado.get('movimientos'):
            print(f"\n💰 MOVIMIENTOS EXTRAÍDOS:")
            for i, mov in enumerate(resultado['movimientos'][:5], 1):
                print(f"   {i}. {mov.get('fecha')} - {mov.get('concepto')} - ${mov.get('monto')}")
        
        # Limpiar
        os.remove(filename)
        
    except ImportError:
        print("⚠️ reportlab no está instalado, instálalo con: pip install reportlab")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🔍 DIAGNÓSTICO DEL SERVIDOR - PROCESAMIENTO INBURSA")
    print("=" * 80)
    
    print("\n1️⃣ Probando con PDF de ejemplo...")
    test_con_pdf_ejemplo()
    
    print(f"\n{'='*80}")
    print("💡 INSTRUCCIONES:")
    print("   1. Ejecuta este script mientras subes tu PDF real")
    print("   2. Los logs detallados aparecerán aquí")
    print("   3. Podemos ver exactamente dónde falla la extracción")
    
    print(f"\n🎯 Para debugging en tiempo real:")
    print("   - Sube tu PDF en la interfaz web")
    print("   - Observa los logs del servidor en la terminal")
    print("   - Los mensajes de debug mostrarán qué encuentra")

if __name__ == "__main__":
    main()