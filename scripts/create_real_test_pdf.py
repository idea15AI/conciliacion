#!/usr/bin/env python3
"""
Crea un PDF de estado de cuenta con el formato exacto del PDF del usuario
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import black, blue, red, green
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.units import inch
import os

def create_real_test_pdf():
    """Crea un PDF con el formato exacto del PDF del usuario"""
    filename = "test_real_format.pdf"
    
    try:
        # Crear documento
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=20,
            alignment=1  # Centrado
        )
        
        # Información del banco (formato del usuario)
        bank_info = [
            ["CUENTA 50058959195 SUCURSAL PUEBLA PLAZA DORADA"],
            ["CLABE 036650500589591954 MONEDA MXN PESO MEXICANO"],
            ["PERIODO Del 01 May. 2025 al 31 May. 2025 FECHA DE CORTE 31 May. 2025"],
            ["31 GAT NO APLICA"],
            ["6.3051% RENDIMIENTOS 309.08"],
            ["5.8119%"],
            ["0.5000% COMISIONES EFECTIVAMENTE COBRADAS"],
            ["EN EL PERIODO 1,258.57"],
        ]
        
        # Agregar información del banco
        for info in bank_info:
            story.append(Paragraph(info[0], styles['Normal']))
        
        story.append(Paragraph("<br/>", styles['Normal']))
        
        # Headers de movimientos (formato del usuario)
        headers = ["FECHA", "REFERENCIA", "CONCEPTO", "CARGOS", "ABONOS", "SALDO"]
        header_table = Table([headers], colWidths=[1*inch, 1.2*inch, 2.5*inch, 1*inch, 1*inch, 1.2*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
        ]))
        story.append(header_table)
        
        # Movimientos con formato exacto del usuario
        movimientos = [
            ["MAY. 01", "3407784114", "BALANCE INICIAL LIQUIDACION ADQUIRENTE CREDITO", "", "165.00", "44,432.09"],
            ["MAY. 02", "3407784117", "TASA DE DESCTO CREDITO", "", "4.60", "44,592.49"],
            ["MAY. 02", "3407784117", "IVA TASA DE DESCTO CREDITO", "", "0.74", "44,591.75"],
            ["MAY. 02", "3407784123", "LIQUIDACION ADQUIRENTE DEBITO", "1,050.00", "", "45,641.75"],
            ["MAY. 02", "3407784128", "TASA DE DESCTO DEBITO", "22.48", "", "45,619.27"],
            ["MAY. 02", "3407784128", "IVA TASA DE DESCTO DEBITO", "3.60", "", "45,615.67"],
            ["MAY. 02", "3408029858", "DEPOSITO TEF", "", "472.46", "46,088.13"],
            ["MAY. 05", "3411389231", "LIQUIDACION ADQUIRENTE DEBITO", "1,115.00", "", "47,203.13"],
        ]
        
        # Crear tabla de movimientos
        for i, mov in enumerate(movimientos):
            # Alternar colores de filas
            bg_color = 'white' if i % 2 == 0 else 'lightblue'
            
            mov_table = Table([mov], colWidths=[1*inch, 1.2*inch, 2.5*inch, 1*inch, 1*inch, 1.2*inch])
            mov_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), bg_color),
                ('ALIGN', (0, 0), (2, 0), 'LEFT'),
                ('ALIGN', (3, 0), (5, 0), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('TOPPADDING', (0, 0), (-1, 0), 4),
                ('GRID', (0, 0), (-1, 0), 0.5, 'gray'),
            ]))
            story.append(mov_table)
        
        # Información adicional (formato del usuario)
        additional_info = [
            "1041881046199 OPERADORA PAYPAL DE MEXICO S DE RL",
            "106",
            "LIQUIDACION ADQ CREDITO-8993380",
            "APLICACION DE TASAS DE DESCUENTO-CREDITO-8993380",
            "Tasa IVA 16.0 %",
            "LIQUIDACION ADQ DEBITO-8993380",
            "APLICACION DE TASAS DE DESCUENTO-DEBITO-8993380",
            "Tasa IVA 16.0 %",
            "LIQUIDACION ADQ DEBITO-8993380",
        ]
        
        story.append(Paragraph("<br/>", styles['Normal']))
        
        for info in additional_info:
            story.append(Paragraph(info, styles['Normal']))
        
        # Construir PDF
        doc.build(story)
        
        print(f"✅ PDF con formato real creado: {filename}")
        print(f"📁 Ubicación: {os.path.abspath(filename)}")
        return filename
        
    except Exception as e:
        print(f"❌ Error creando PDF: {e}")
        return None

if __name__ == "__main__":
    create_real_test_pdf() 