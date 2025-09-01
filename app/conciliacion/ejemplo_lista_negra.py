#!/usr/bin/env python3
"""
Ejemplo de uso del servicio de Lista Negra SAT
Muestra cómo usar las funciones corregidas para obtener KPIs precisos
"""

from app.conciliacion.lista_negra_service import ListaNegraService
from app.core.database import get_db

def ejemplo_uso_lista_negra():
    """
    Ejemplo completo de uso del servicio de lista negra
    """
    
    # Obtener sesión de base de datos
    db = next(get_db())
    
    try:
        # Crear instancia del servicio
        lista_negra_service = ListaNegraService(db)
        
        # Parámetros de ejemplo
        rfc_empresa = "IDE2001209V6"  # RFC de tu empresa
        fecha_inicio = "2024-01-01"   # Fecha inicio (opcional)
        fecha_fin = "2024-12-31"      # Fecha fin (opcional)
        
        print(f"🔍 Consultando Lista Negra SAT para empresa: {rfc_empresa}")
        print(f"📅 Período: {fecha_inicio} a {fecha_fin}")
        print("=" * 60)
        
        # 1. Obtener KPIs resumen
        print("\n📊 KPIs RESUMEN:")
        kpis = lista_negra_service.obtener_kpis_resumen(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        print(f"   Total Detectados en Lista Negra: {kpis.get('total_detectados', 0)}")
        print(f"   Monto Total en Riesgo: ${kpis.get('monto_total_en_riesgo', 0):,.2f}")
        print(f"   Total Contribuyentes Revisados: {kpis.get('total_contribuyentes_revisados', 0)}")
        print(f"   Total Clientes Revisados: {kpis.get('total_clientes_revisados', 0)}")
        print(f"   Total Proveedores Revisados: {kpis.get('total_proveedores_revisados', 0)}")
        
        # 2. Obtener distribución por nivel de riesgo
        print("\n🎯 DISTRIBUCIÓN POR NIVEL DE RIESGO:")
        distribucion = lista_negra_service.obtener_distribucion_riesgo(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        print("   Conteo por nivel:")
        for nivel, cantidad in distribucion.get('conteo', {}).items():
            print(f"     {nivel}: {cantidad}")
        
        print("   Montos por nivel:")
        for nivel, monto in distribucion.get('montos', {}).items():
            print(f"     {nivel}: ${monto:,.2f}")
        
        # 3. Obtener agregados de riesgo fiscal
        print("\n💰 AGREGADOS DE RIESGO FISCAL:")
        agregados_fiscal = lista_negra_service.obtener_agregados_riesgo_fiscal(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        for agregado in agregados_fiscal:
            nivel = agregado.get('nivel_riesgo', 'N/A')
            iva_riesgo = agregado.get('iva_riesgo', 0)
            isr_riesgo = agregado.get('isr_riesgo', 0)
            print(f"     {nivel}:")
            print(f"       IVA en Riesgo: ${iva_riesgo:,.2f}")
            print(f"       ISR en Riesgo: ${isr_riesgo:,.2f}")
        
        # 4. Obtener clientes en lista negra
        print("\n👥 CLIENTES EN LISTA NEGRA:")
        clientes_ln = lista_negra_service.obtener_clientes_lista_negra(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        print(f"   Total clientes en lista negra: {len(clientes_ln)}")
        for i, cliente in enumerate(clientes_ln[:5], 1):  # Mostrar solo los primeros 5
            print(f"     {i}. {cliente.get('nombre', 'Sin nombre')} - {cliente.get('rfc', 'N/A')}")
            print(f"        Nivel: {cliente.get('nivel_riesgo', 'N/A')} | Monto: ${cliente.get('monto_total', 0):,.2f}")
        
        # 5. Obtener proveedores en lista negra
        print("\n🏢 PROVEEDORES EN LISTA NEGRA:")
        proveedores_ln = lista_negra_service.obtener_proveedores_lista_negra(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        print(f"   Total proveedores en lista negra: {len(proveedores_ln)}")
        for i, proveedor in enumerate(proveedores_ln[:5], 1):  # Mostrar solo los primeros 5
            print(f"     {i}. {proveedor.get('nombre', 'Sin nombre')} - {proveedor.get('rfc', 'N/A')}")
            print(f"        Nivel: {proveedor.get('nivel_riesgo', 'N/A')} | Monto: ${proveedor.get('monto_total', 0):,.2f}")
        
        # 6. Generar reporte completo
        print("\n📋 REPORTE COMPLETO:")
        reporte_completo = lista_negra_service.generar_reporte_completo(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        print(f"   Fecha de generación: {reporte_completo.get('fecha_generacion', 'N/A')}")
        print(f"   Resumen:")
        resumen = reporte_completo.get('resumen', {})
        print(f"     Total clientes en lista negra: {resumen.get('total_clientes_ln', 0)}")
        print(f"     Total proveedores en lista negra: {resumen.get('total_proveedores_ln', 0)}")
        print(f"     Total detectados: {resumen.get('total_detectados', 0)}")
        print(f"     Monto total en riesgo: ${resumen.get('monto_total_riesgo', 0):,.2f}")
        
        print("\n✅ Consulta completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error en la consulta: {e}")
        
    finally:
        db.close()


def ejemplo_consulta_simple():
    """
    Ejemplo de consulta simple sin fechas
    """
    
    db = next(get_db())
    
    try:
        lista_negra_service = ListaNegraService(db)
        rfc_empresa = "IDE2001209V6"
        
        print(f"🔍 Consulta simple para empresa: {rfc_empresa}")
        print("=" * 40)
        
        # Solo KPIs sin filtro de fechas
        kpis = lista_negra_service.obtener_kpis_resumen(rfc_empresa=rfc_empresa)
        
        print(f"Total Contribuyentes Revisados: {kpis.get('total_contribuyentes_revisados', 0)}")
        print(f"Total Clientes Revisados: {kpis.get('total_clientes_revisados', 0)}")
        print(f"Total Proveedores Revisados: {kpis.get('total_proveedores_revisados', 0)}")
        print(f"Total Detectados en Lista Negra: {kpis.get('total_detectados', 0)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        db.close()


if __name__ == "__main__":
    print("🚨 SISTEMA DE LISTA NEGRA SAT")
    print("=" * 60)
    
    # Ejecutar ejemplo completo
    ejemplo_uso_lista_negra()
    
    print("\n" + "=" * 60)
    
    # Ejecutar ejemplo simple
    ejemplo_consulta_simple()
