#!/usr/bin/env python3
"""
Script para crear un PDF de prueba simple
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def crear_pdf_prueba():
    """Crea un PDF de prueba simple"""
    c = canvas.Canvas("test_simple.pdf", pagesize=letter)
    
    # Título
    c.drawString(100, 750, "ESTADO DE CUENTA BANCARIO")
    c.drawString(100, 730, "BANCO: SANTANDER")
    
    # Encabezados
    c.drawString(100, 700, "FECHA")
    c.drawString(200, 700, "CONCEPTO")
    c.drawString(350, 700, "CARGOS")
    c.drawString(450, 700, "ABONOS")
    c.drawString(550, 700, "SALDO")
    
    # Línea separadora
    c.line(100, 690, 600, 690)
    
    # Movimientos de prueba
    movimientos = [
        ("01/01/24", "DEPOSITO EN EFECTIVO", "", "$1,000.00", "$1,000.00"),
        ("02/01/24", "RETIRO EN CAJERO", "$500.00", "", "$500.00"),
        ("03/01/24", "PAGO NOMINA", "", "$2,500.00", "$3,000.00"),
        ("04/01/24", "COMISION MANTENIMIENTO", "$50.00", "", "$2,950.00"),
    ]
    
    y_pos = 660
    for fecha, concepto, cargos, abonos, saldo in movimientos:
        c.drawString(100, y_pos, fecha)
        c.drawString(200, y_pos, concepto)
        c.drawString(350, y_pos, cargos)
        c.drawString(450, y_pos, abonos)
        c.drawString(550, y_pos, saldo)
        y_pos -= 20
    
    c.save()
    print("✅ PDF de prueba creado: test_simple.pdf")

if __name__ == "__main__":
    crear_pdf_prueba() 