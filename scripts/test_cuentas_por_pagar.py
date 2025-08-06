#!/usr/bin/env python3
"""
Script para crear un PDF con el caso problemático de CUENTAS POR PAGAR - SAP
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def crear_pdf_cuentas_por_pagar():
    """Crea un PDF con el caso problemático de CUENTAS POR PAGAR - SAP"""
    c = canvas.Canvas("test_cuentas_por_pagar.pdf", pagesize=letter)
    
    # Título
    c.drawString(100, 750, "DETALLE DE MOVIMIENTOS (PESOS)")
    c.drawString(100, 730, "BANORTE - Caso Problemático")
    
    # Encabezados
    c.drawString(100, 700, "FECHA")
    c.drawString(200, 700, "DESCRIPCIÓN / ESTABLECIMIENTO")
    c.drawString(400, 700, "MONTO DEL DEPOSITO")
    c.drawString(500, 700, "MONTO DEL RETIRO")
    c.drawString(600, 700, "SALDO")
    
    # Línea separadora
    c.line(100, 690, 700, 690)
    
    # Movimientos de prueba con el caso problemático
    movimientos = [
        ("11-ENE-23", "CUENTAS POR PAGAR - SAP 0001072097 000000662023REPP", "437,359.86", "", "1,540,001.84"),
        ("12-ENE-23", "SPEI RECIBIDO, BCO:0036 INBURSA HR LIQ: 09:32:07 DEL CLIENTE MARISA LOPEZ FERNANDEZ", "15,544.00", "", "1,555,545.84"),
        ("13-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000000656 DE LA CUENTA 0557374518", "", "110,254.00", "1,445,291.84"),
        ("14-ENE-23", "DEP.EFECTIVO", "6,432.00", "", "1,451,723.84"),
        ("15-ENE-23", "COMPRA ORDEN DE PAGO SPEI", "", "70,000.00", "1,381,723.84"),
    ]
    
    y_pos = 660
    for fecha, descripcion, deposito, retiro, saldo in movimientos:
        # Fecha
        c.drawString(100, y_pos, fecha)
        
        # Descripción (corta)
        if len(descripcion) > 30:
            desc_corta = descripcion[:30] + "..."
        else:
            desc_corta = descripcion
        c.drawString(200, y_pos, desc_corta)
        
        # Monto del depósito
        c.drawString(400, y_pos, deposito)
        
        # Monto del retiro
        c.drawString(500, y_pos, retiro)
        
        # Saldo
        c.drawString(600, y_pos, saldo)
        
        y_pos -= 20
        
        # Si la descripción es larga, agregar línea adicional
        if len(descripcion) > 30:
            y_pos -= 15
            c.drawString(200, y_pos, descripcion[30:60] + "..." if len(descripcion) > 60 else descripcion[30:])
            y_pos -= 20
    
    c.save()
    print("✅ PDF con caso problemático creado: test_cuentas_por_pagar.pdf")

if __name__ == "__main__":
    crear_pdf_cuentas_por_pagar() 