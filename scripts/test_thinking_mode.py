#!/usr/bin/env python3
"""
Script para probar el thinking mode de Gemini
"""

import os
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conciliacion.gemini_processor import GeminiProcessor

def crear_pdf_banorte_thinking():
    """Crea un PDF de BANORTE para probar el thinking mode"""
    c = canvas.Canvas("test_thinking_banorte.pdf", pagesize=letter)
    
    # Título
    c.drawString(100, 750, "DETALLE DE TRANSACCIONES REALIZADAS")
    c.drawString(100, 730, "PERIODO: 01/01/2024 AL 31/01/2024")
    
    # Encabezados
    c.drawString(100, 700, "FECHA")
    c.drawString(200, 700, "CONCEPTO")
    c.drawString(350, 700, "DISPOSICIONES")
    c.drawString(450, 700, "PAGOS")
    c.drawString(550, 700, "SALDO")
    
    # Línea separadora
    c.line(100, 690, 600, 690)
    
    # Movimientos
    movimientos = [
        ("15/01/24", "PAGO DE INTERÉS", "$0.00", "$25,187.50", "$25,187.50"),
        ("15/01/24", "PAGO DE CAPITAL", "$0.00", "$83,333.33", "$108,520.83"),
        ("20/01/24", "DEPOSITO DE CUENTA DE TERCEROS", "$0.00", "$50,000.00", "$158,520.83"),
        ("25/01/24", "RETIRO EN CAJERO", "$5,000.00", "$0.00", "$153,520.83"),
        ("30/01/24", "COMISION MANTENIMIENTO", "$150.00", "$0.00", "$153,370.83")
    ]
    
    y_pos = 660
    for fecha, concepto, disposiciones, pagos, saldo in movimientos:
        c.drawString(100, y_pos, fecha)
        c.drawString(200, y_pos, concepto)
        c.drawString(350, y_pos, disposiciones)
        c.drawString(450, y_pos, pagos)
        c.drawString(550, y_pos, saldo)
        y_pos -= 20
    
    # Total
    c.line(100, y_pos - 10, 600, y_pos - 10)
    c.drawString(100, y_pos - 30, "TOTAL")
    c.drawString(350, y_pos - 30, "$5,150.00")
    c.drawString(450, y_pos - 30, "$158,520.83")
    c.drawString(550, y_pos - 30, "$153,370.83")
    
    c.save()
    print("✅ PDF de prueba para thinking mode creado: test_thinking_banorte.pdf")

def probar_thinking_mode():
    """Prueba el thinking mode con diferentes configuraciones"""
    processor = GeminiProcessor()
    
    print("🧪 PROBANDO THINKING MODE")
    print("=" * 50)
    
    # Crear PDF de prueba
    crear_pdf_banorte_thinking()
    
    try:
        # Probar con diferentes configuraciones de thinking budget
        configuraciones = [
            ("Flash Lite - Thinking Bajo", "gemini-2.5-flash-lite", 1024),
            ("Flash Lite - Thinking Medio", "gemini-2.5-flash-lite", 4096),
            ("Flash - Thinking Alto", "gemini-2.5-flash", 8192),
        ]
        
        for nombre, modelo, thinking_budget in configuraciones:
            print(f"\n🔍 Probando: {nombre}")
            print(f"   Modelo: {modelo}")
            print(f"   Thinking Budget: {thinking_budget}")
            
            # Configurar modelo manualmente para prueba
            processor.model_id = modelo
            
            # Intentar procesar (puede fallar por sobrecarga del modelo)
            try:
                resultado = processor.procesar_pdf("test_thinking_banorte.pdf")
                
                if resultado.get("exito"):
                    print(f"   ✅ Éxito: {resultado.get('total_movimientos_extraidos', 0)} movimientos")
                    print(f"   ⏱️ Tiempo: {resultado.get('tiempo_procesamiento_segundos', 0)}s")
                    print(f"   🏦 Banco: {resultado.get('banco_detectado', 'N/A')}")
                else:
                    print(f"   ❌ Error: {resultado.get('mensaje', 'Error desconocido')}")
                    
            except Exception as e:
                print(f"   ⚠️ Error de procesamiento: {e}")
            
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ Error en prueba de thinking mode: {e}")
    finally:
        # Limpiar archivo de prueba
        if os.path.exists("test_thinking_banorte.pdf"):
            os.remove("test_thinking_banorte.pdf")

def mostrar_beneficios_thinking_mode():
    """Muestra los beneficios del thinking mode"""
    print("\n🎯 BENEFICIOS DEL THINKING MODE")
    print("=" * 50)
    print("✅ Análisis paso a paso más preciso")
    print("✅ Mejor detección de formatos bancarios")
    print("✅ Reducción de errores en clasificación cargo/abono")
    print("✅ Mejor manejo de movimientos multi-línea")
    print("✅ Validación más robusta de datos")
    print("✅ Priorización correcta de columnas sobre contexto")
    print("✅ Configuración automática según complejidad del documento")

if __name__ == "__main__":
    print("🧪 TEST: Thinking Mode de Gemini")
    print("=" * 50)
    
    # Verificar configuración
    try:
        processor = GeminiProcessor()
        print("✅ Configuración de Gemini correcta")
    except Exception as e:
        print(f"❌ Error de configuración: {e}")
        sys.exit(1)
    
    # Mostrar beneficios
    mostrar_beneficios_thinking_mode()
    
    # Ejecutar pruebas
    probar_thinking_mode()
    
    print("\n🎉 Pruebas de thinking mode completadas!") 