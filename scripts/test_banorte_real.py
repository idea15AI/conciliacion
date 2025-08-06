#!/usr/bin/env python3
"""
Script para crear un PDF con formato BANORTE real basado en la imagen
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def crear_pdf_banorte_real():
    """Crea un PDF con formato BANORTE real"""
    c = canvas.Canvas("test_banorte_real.pdf", pagesize=letter)
    
    # Título
    c.drawString(100, 750, "DETALLE DE MOVIMIENTOS (PESOS)")
    c.drawString(100, 730, "Enlace Negocios Basica")
    
    # Encabezados
    c.drawString(100, 700, "FECHA")
    c.drawString(200, 700, "DESCRIPCIÓN / ESTABLECIMIENTO")
    c.drawString(400, 700, "MONTO DEL DEPOSITO")
    c.drawString(500, 700, "MONTO DEL RETIRO")
    c.drawString(600, 700, "SALDO")
    
    # Línea separadora
    c.line(100, 690, 700, 690)
    
    # Movimientos de prueba basados en la imagen
    movimientos = [
        ("31-DIC-22", "SALDO INICIAL", "", "", "1,000,000.00"),
        ("03-ENE-23", "DEPOSITO DE CUENTA DE TERCEROS 0000000655 DE LA CUENTA 0557374517 PAGO FACT 655 RENTA JUAREZ ENERO 2023", "197,200.00", "", "1,197,200.00"),
        ("03-ENE-23", "SPEI RECIBIDO, BCO:0036 INBURSA HR LIQ: 09:32:07 DEL CLIENTE MARISA LOPEZ FERNANDEZ DE LA CLABE 036669500469694771 CON RFC LOFM8906256IA CONCEPTO: renta enero 2023 REFERENCIA: 0000001 CVE RAST: 036APPM15012023107434731", "11,658.00", "", "1,208,858.00"),
        ("04-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000000656 DE LA CUENTA 0557374518 PAGO FACT 656 RENTA JUAREZ ENERO 2023", "", "110,254.00", "1,098,604.00"),
        ("04-ENE-23", "COMPRA ORDEN DE PAGO SPEI", "", "70,000.00", "1,028,604.00"),
        ("05-ENE-23", "SPEI RECIBIDO, BCO:0137 BANCOPPEL HR LIQ: 16:20:47 DEL CLIENTE SILVIANO LOPEZ MONTIEL DE LA CLABE 137650101050420739 CON RFC LOMS761103665 CONCEPTO: pago de renta REFERENCIA: 7183067 CVE RAST: 50110739TRANSBPI71830677", "7,540.00", "", "1,036,144.00"),
        ("11-ENE-23", "CUENTAS POR PAGAR - SAP", "437,359.86", "", "1,473,503.86"),
        ("12-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000000657 DE LA CUENTA 0557374519 PAGO FACT 657 RENTA JUAREZ ENERO 2023", "", "160,593.00", "1,312,910.86"),
        ("12-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000000658 DE LA CUENTA 0557374520 PAGO FACT 658 RENTA JUAREZ ENERO 2023", "", "124,453.00", "1,188,457.86"),
        ("12-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000000659 DE LA CUENTA 0557374521 PAGO FACT 659 RENTA JUAREZ ENERO 2023", "", "120,593.00", "1,067,864.86"),
        ("12-ENE-23", "TRASPASO A CUENTA DE TERCEROS 0000000660 DE LA CUENTA 0557374522 PAGO FACT 660 RENTA JUAREZ ENERO 2023", "", "120,593.00", "947,271.86"),
        ("12-ENE-23", "COMPRA ORDEN DE PAGO SPEI", "", "3,356.81", "943,915.05"),
        ("15-ENE-23", "SPEI RECIBIDO, BCO:0036 INBURSA HR LIQ: 09:32:07 DEL CLIENTE MARISA LOPEZ FERNANDEZ DE LA CLABE 036669500469694771 CON RFC LOFM8906256IA CONCEPTO: renta enero 2023 REFERENCIA: 0000001 CVE RAST: 036APPM15012023107434731", "15,544.00", "", "959,459.05"),
        ("17-ENE-23", "SPEI RECIBIDO, BCO:0137 BANCOPPEL HR LIQ: 16:20:47 DEL CLIENTE SILVIANO LOPEZ MONTIEL DE LA CLABE 137650101050420739 CON RFC LOMS761103665 CONCEPTO: pago de renta REFERENCIA: 7183067 CVE RAST: 50110739TRANSBPI71830677", "6,430.00", "", "965,889.05"),
        ("24-ENE-23", "SPEI RECIBIDO, BCO:0014 SANTANDER HR LIQ: 13:28:21 DEL CLIENTE GASOLINERA RASAGUI SA DE CV DE LA CLABE 014650920020900237 CON RFC GRA141128124 CONCEPTO: PAGO RENTA REFERENCIA: 3426803 CVE RAST: 2023012440014 BET0000434268030", "104,310.84", "", "1,070,199.89"),
        ("30-ENE-23", "DEP.EFECTIVO", "6,432.00", "", "1,076,631.89"),
        ("30-ENE-23", "SPEI RECIBIDO, BCO:0012 BBVA BANCOMER HR LIQ: 13:56:27 DEL CLIENTE DANIELA GARCIA CRUZ DE LA CLABE 012650011773857069 CON RFC GACD910824294 CONCEPTO: Renta lavado REFERENCIA: 3001230 CVE RAST: MBAN01002301300089750182", "11,916.00", "", "1,088,547.89"),
    ]
    
    y_pos = 660
    for fecha, descripcion, deposito, retiro, saldo in movimientos:
        # Fecha
        c.drawString(100, y_pos, fecha)
        
        # Descripción (corta)
        if len(descripcion) > 25:
            desc_corta = descripcion[:25] + "..."
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
        if len(descripcion) > 25:
            y_pos -= 15
            c.drawString(200, y_pos, descripcion[25:50] + "..." if len(descripcion) > 50 else descripcion[25:])
            y_pos -= 20
    
    c.save()
    print("✅ PDF con formato BANORTE real creado: test_banorte_real.pdf")

if __name__ == "__main__":
    crear_pdf_banorte_real() 