#!/usr/bin/env python3
"""
Script para crear un PDF con formato SPEI RECIBIDO para probar la detección mejorada
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def crear_pdf_spei_format():
    """Crea un PDF con formato SPEI RECIBIDO"""
    c = canvas.Canvas("test_spei_format.pdf", pagesize=letter)
    
    # Título
    c.drawString(100, 750, "ESTADO DE CUENTA BANCARIO")
    c.drawString(100, 730, "FORMATO SPEI RECIBIDO")
    
    # Movimientos de prueba basados en el ejemplo del usuario
    movimientos = [
        ("15-ENE-23", "036APPM15012023107434731", "SPEI RECIBIDO, BCO:0036 INBURSA HR LIQ: 09:32:07 DEL CLIENTE MARISA LOPEZ FERNANDEZ DE LA CLABE 036669500469694771 CON RFC LOFM8906256IA CONCEPTO: renta enero 2023 REFERENCIA: 0000001 CVE RAST: 036APPM15012023107434731", "15,544.00", "1,150,410.03"),
        ("17-ENE-23", "50110739TRANSBPI71830677", "SPEI RECIBIDO, BCO:0137 BANCOPPEL HR LIQ: 16:20:47 DEL CLIENTE SILVIANO LOPEZ MONTIEL DE LA CLABE 137650101050420739 CON RFC LOMS761103665 CONCEPTO: pago de renta REFERENCIA: 7183067 CVE RAST: 50110739TRANSBPI71830677", "6,430.00", "1,156,840.03"),
        ("24-ENE-23", "2023012440014 BET0000434268030", "SPEI RECIBIDO, BCO:0014 SANTANDER HR LIQ: 13:28:21 DEL CLIENTE GASOLINERA RASAGUI SA DE CV DE LA CLABE 014650920020900237 CON RFC GRA141128124 CONCEPTO: PAGO RENTA REFERENCIA: 3426803 CVE RAST: 2023012440014 BET0000434268030", "104,310.84", "1,261,150.87"),
        ("30-ENE-23", "DEP.EFECTIVO", "DEP.EFECTIVO", "6,432.00", "1,267,582.87"),
        ("30-ENE-23", "MBAN01002301300089750182", "SPEI RECIBIDO, BCO:0012 BBVA BANCOMER HR LIQ: 13:56:27 DEL CLIENTE DANIELA GARCIA CRUZ DE LA CLABE 012650011773857069 CON RFC GACD910824294 CONCEPTO: Renta lavado REFERENCIA: 3001230 CVE RAST: MBAN01002301300089750182", "11,916.00", "1,279,498.87"),
    ]
    
    # Encabezados
    c.drawString(100, 700, "FECHA")
    c.drawString(200, 700, "REFERENCIA")
    c.drawString(350, 700, "CONCEPTO")
    c.drawString(500, 700, "MONTO")
    c.drawString(600, 700, "SALDO")
    
    # Línea separadora
    c.line(100, 690, 700, 690)
    
    y_pos = 660
    for fecha, referencia, concepto, monto, saldo in movimientos:
        # Fecha
        c.drawString(100, y_pos, fecha)
        
        # Referencia (corta)
        if len(referencia) > 20:
            ref_corta = referencia[:20] + "..."
        else:
            ref_corta = referencia
        c.drawString(200, y_pos, ref_corta)
        
        # Concepto (corto)
        if len(concepto) > 30:
            concepto_corto = concepto[:30] + "..."
        else:
            concepto_corto = concepto
        c.drawString(350, y_pos, concepto_corto)
        
        # Monto
        c.drawString(500, y_pos, monto)
        
        # Saldo
        c.drawString(600, y_pos, saldo)
        
        y_pos -= 20
        
        # Si el concepto es largo, agregar línea adicional
        if len(concepto) > 30:
            y_pos -= 15
            c.drawString(350, y_pos, concepto[30:60] + "..." if len(concepto) > 60 else concepto[30:])
            y_pos -= 20
    
    c.save()
    print("✅ PDF con formato SPEI RECIBIDO creado: test_spei_format.pdf")

if __name__ == "__main__":
    crear_pdf_spei_format() 