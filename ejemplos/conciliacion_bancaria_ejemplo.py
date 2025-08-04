#!/usr/bin/env python3
"""
Ejemplo práctico de uso del módulo de conciliación bancaria avanzada

Este script demuestra cómo usar todas las funcionalidades del módulo
de conciliación bancaria paso a paso.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
BASE_URL = "http://localhost:8000/api/v1/conciliacion"
RFC_EMPRESA = "TST123456789"  # RFC de empresa de prueba

class EjemploConciliacionBancaria:
    """
    Clase para demostrar el uso completo del módulo de conciliación bancaria
    """
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def verificar_servidor(self):
        """Verifica que el servidor esté funcionando"""
        try:
            response = self.session.get(f"{self.base_url.replace('/conciliacion', '')}/health")
            if response.status_code == 200:
                logger.info("✅ Servidor funcionando correctamente")
                return True
            else:
                logger.error(f"❌ Servidor respondió con código {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ No se pudo conectar al servidor: {e}")
            return False
    
    def mostrar_endpoints_disponibles(self):
        """Muestra información sobre los endpoints disponibles"""
        logger.info("🔗 Endpoints disponibles del módulo de conciliación:")
        logger.info(f"   📤 Subir estado de cuenta: POST {self.base_url}/subir-estado-cuenta")
        logger.info(f"   ⚡ Ejecutar conciliación: POST {self.base_url}/ejecutar")
        logger.info(f"   📊 Obtener reporte: GET {self.base_url}/reporte/{{empresa_id}}")
        logger.info(f"   📋 Listar movimientos: GET {self.base_url}/movimientos/{{empresa_id}}")
        logger.info(f"   📁 Listar archivos: GET {self.base_url}/archivos/{{empresa_id}}")
        logger.info(f"   📈 Estadísticas: GET {self.base_url}/estadisticas/{{empresa_id}}")
    
    def crear_pdf_demo(self) -> bytes:
        """
        Crea un PDF de demostración simulando un estado de cuenta
        
        NOTA: En un caso real, cargarías un PDF real del banco
        """
        logger.info("📄 Creando PDF de demostración...")
        
        # Para este ejemplo, creamos un PDF simple con contenido de texto
        # En la vida real, usarías un PDF real de un banco
        pdf_content = b"""
        %PDF-1.4
        1 0 obj
        <<
        /Type /Catalog
        /Pages 2 0 R
        >>
        endobj
        
        2 0 obj
        <<
        /Type /Pages
        /Kids [3 0 R]
        /Count 1
        >>
        endobj
        
        3 0 obj
        <<
        /Type /Page
        /Parent 2 0 R
        /MediaBox [0 0 612 792]
        /Contents 4 0 R
        >>
        endobj
        
        4 0 obj
        <<
        /Length 200
        >>
        stream
        BT
        /F1 12 Tf
        100 700 Td
        (ESTADO DE CUENTA BANCARIO - BBVA) Tj
        0 -20 Td
        (PERIODO: 01/01/2024 - 31/01/2024) Tj
        0 -20 Td
        (CUENTA: ****1234) Tj
        0 -40 Td
        (15/01/2024 PAGO FACTURA A1234 EMPRESA XYZ   -1,250.50) Tj
        ET
        endstream
        endobj
        
        xref
        0 5
        0000000000 65535 f 
        0000000009 00000 n 
        0000000058 00000 n 
        0000000115 00000 n 
        0000000200 00000 n 
        trailer
        <<
        /Size 5
        /Root 1 0 R
        >>
        startxref
        450
        %%EOF
        """
        
        logger.info("✅ PDF de demostración creado")
        return pdf_content
    
    def ejemplo_subir_estado_cuenta(self):
        """
        Ejemplo 1: Subir y procesar estado de cuenta con OCR
        """
        logger.info("\n" + "="*60)
        logger.info("📤 EJEMPLO 1: Subir Estado de Cuenta")
        logger.info("="*60)
        
        try:
            # Crear PDF de demostración
            pdf_content = self.crear_pdf_demo()
            
            # Subir archivo
            files = {
                'file': ('estado_cuenta_demo.pdf', pdf_content, 'application/pdf')
            }
            params = {
                'rfc_empresa': RFC_EMPRESA
            }
            
            logger.info(f"📤 Subiendo estado de cuenta para empresa {RFC_EMPRESA}...")
            
            response = self.session.post(
                f"{self.base_url}/subir-estado-cuenta",
                files=files,
                params=params
            )
            
            if response.status_code == 200:
                resultado = response.json()
                logger.info("✅ Estado de cuenta procesado exitosamente:")
                logger.info(f"   📁 Archivo ID: {resultado.get('archivo_id')}")
                logger.info(f"   🏦 Banco detectado: {resultado.get('banco_detectado')}")
                logger.info(f"   📊 Movimientos extraídos: {resultado.get('total_movimientos_extraidos')}")
                logger.info(f"   ⏱️  Tiempo de procesamiento: {resultado.get('tiempo_procesamiento_segundos')}s")
                
                if resultado.get('errores'):
                    logger.warning(f"   ⚠️  Errores: {len(resultado['errores'])}")
                
                return resultado.get('archivo_id')
            else:
                logger.error(f"❌ Error subiendo archivo: {response.status_code}")
                logger.error(f"   Detalle: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error en ejemplo de subida: {e}")
            return None
    
    def ejemplo_ejecutar_conciliacion(self):
        """
        Ejemplo 2: Ejecutar proceso de conciliación automática
        """
        logger.info("\n" + "="*60)
        logger.info("⚡ EJEMPLO 2: Ejecutar Conciliación")
        logger.info("="*60)
        
        try:
            # Configurar parámetros de conciliación
            parametros = {
                "rfc_empresa": RFC_EMPRESA,
                "mes": datetime.now().month,
                "anio": datetime.now().year,
                "tolerancia_monto": 1.00,
                "dias_tolerancia": 3,
                "forzar_reproceso": True  # Para el ejemplo
            }
            
            logger.info(f"⚡ Ejecutando conciliación para {RFC_EMPRESA}...")
            logger.info(f"   📅 Período: {parametros['mes']}/{parametros['anio']}")
            logger.info(f"   💰 Tolerancia monto: ${parametros['tolerancia_monto']}")
            logger.info(f"   📅 Tolerancia días: {parametros['dias_tolerancia']}")
            
            response = self.session.post(
                f"{self.base_url}/ejecutar",
                json=parametros
            )
            
            if response.status_code == 200:
                resultado = response.json()
                estadisticas = resultado.get('estadisticas', {})
                
                logger.info("✅ Conciliación completada:")
                logger.info(f"   📊 Total movimientos: {estadisticas.get('total_movimientos_bancarios', 0)}")
                logger.info(f"   ✅ Conciliados: {estadisticas.get('movimientos_conciliados', 0)}")
                logger.info(f"   ⏳ Pendientes: {estadisticas.get('movimientos_pendientes', 0)}")
                logger.info(f"   📈 Porcentaje éxito: {estadisticas.get('porcentaje_conciliacion', 0):.2f}%")
                logger.info(f"   ⏱️  Tiempo total: {resultado.get('tiempo_total_segundos', 0)}s")
                
                # Mostrar estadísticas por método
                metodos = [
                    ('exacto', 'Match Exacto'),
                    ('referencia', 'Match Referencia'),
                    ('aproximado', 'Match Aproximado'),
                    ('complemento_ppd', 'Complementos PPD'),
                    ('heuristica', 'Heurística'),
                    ('ml_patron', 'Patrones ML')
                ]
                
                logger.info("\n   📊 Conciliaciones por método:")
                for metodo_clave, metodo_nombre in metodos:
                    cantidad = estadisticas.get(f'conciliados_{metodo_clave}', 0)
                    if cantidad > 0:
                        logger.info(f"      - {metodo_nombre}: {cantidad}")
                
                # Mostrar alertas críticas
                alertas = resultado.get('alertas_criticas', [])
                if alertas:
                    logger.warning(f"\n   🚨 Alertas críticas: {len(alertas)}")
                    for alerta in alertas[:3]:  # Mostrar solo las primeras 3
                        logger.warning(f"      - {alerta.get('tipo')}: {alerta.get('mensaje')}")
                
                # Mostrar sugerencias
                sugerencias = resultado.get('sugerencias', [])
                if sugerencias:
                    logger.info(f"\n   💡 Sugerencias: {len(sugerencias)}")
                
                return True
            else:
                logger.error(f"❌ Error ejecutando conciliación: {response.status_code}")
                logger.error(f"   Detalle: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en ejemplo de conciliación: {e}")
            return False
    
    def ejemplo_obtener_reporte(self, empresa_id: int = 1):
        """
        Ejemplo 3: Obtener reporte detallado de conciliación
        """
        logger.info("\n" + "="*60)
        logger.info("📊 EJEMPLO 3: Obtener Reporte")
        logger.info("="*60)
        
        try:
            # Parámetros del reporte
            params = {
                'mes': datetime.now().month,
                'anio': datetime.now().year
            }
            
            logger.info(f"📊 Obteniendo reporte para empresa ID {empresa_id}...")
            
            response = self.session.get(
                f"{self.base_url}/reporte/{empresa_id}",
                params=params
            )
            
            if response.status_code == 200:
                reporte = response.json()
                
                logger.info("✅ Reporte generado exitosamente:")
                logger.info(f"   🏢 Empresa: {reporte.get('rfc_empresa')}")
                logger.info(f"   📅 Período: {reporte.get('periodo_inicio')} - {reporte.get('periodo_fin')}")
                
                # Estadísticas del reporte
                stats = reporte.get('estadisticas', {})
                logger.info(f"   📊 Estadísticas:")
                logger.info(f"      - Total movimientos: {stats.get('total_movimientos_bancarios', 0)}")
                logger.info(f"      - Conciliados: {stats.get('movimientos_conciliados', 0)}")
                logger.info(f"      - Pendientes: {stats.get('movimientos_pendientes', 0)}")
                logger.info(f"      - Tasa éxito: {stats.get('porcentaje_conciliacion', 0):.2f}%")
                
                # Movimientos pendientes
                pendientes = reporte.get('movimientos_pendientes', [])
                if pendientes:
                    logger.info(f"\n   ⏳ Movimientos pendientes: {len(pendientes)}")
                    for mov in pendientes[:3]:  # Mostrar solo los primeros 3
                        logger.info(f"      - ${mov.get('monto')} - {mov.get('concepto', '')[:50]}...")
                
                # Alertas
                alertas = reporte.get('alertas_criticas', [])
                if alertas:
                    logger.warning(f"\n   🚨 Alertas críticas: {len(alertas)}")
                
                # Sugerencias de mejora
                sugerencias = reporte.get('sugerencias_mejora', [])
                if sugerencias:
                    logger.info(f"\n   💡 Sugerencias de mejora:")
                    for sugerencia in sugerencias:
                        logger.info(f"      - {sugerencia}")
                
                return True
            else:
                logger.error(f"❌ Error obteniendo reporte: {response.status_code}")
                logger.error(f"   Detalle: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en ejemplo de reporte: {e}")
            return False
    
    def ejemplo_listar_movimientos(self, empresa_id: int = 1):
        """
        Ejemplo 4: Listar movimientos con filtros
        """
        logger.info("\n" + "="*60)
        logger.info("📋 EJEMPLO 4: Listar Movimientos")
        logger.info("="*60)
        
        try:
            # Parámetros de filtrado
            params = {
                'page': 1,
                'size': 10,
                'sort_by': 'fecha',
                'sort_order': 'desc'
            }
            
            logger.info(f"📋 Listando movimientos para empresa ID {empresa_id}...")
            
            response = self.session.get(
                f"{self.base_url}/movimientos/{empresa_id}",
                params=params
            )
            
            if response.status_code == 200:
                resultado = response.json()
                movimientos = resultado.get('items', [])
                
                logger.info("✅ Movimientos obtenidos:")
                logger.info(f"   📊 Total: {resultado.get('total', 0)}")
                logger.info(f"   📄 Página: {resultado.get('page', 1)} de {resultado.get('pages', 1)}")
                logger.info(f"   📋 Mostrando: {len(movimientos)} movimientos")
                
                if movimientos:
                    logger.info("\n   💳 Movimientos recientes:")
                    for mov in movimientos:
                        estado_emoji = {
                            'PENDIENTE': '⏳',
                            'CONCILIADO': '✅',
                            'MANUAL': '🔧',
                            'DESCARTADO': '❌'
                        }.get(mov.get('estado', ''), '❓')
                        
                        logger.info(f"      {estado_emoji} ${mov.get('monto')} - {mov.get('concepto', '')[:50]}...")
                        logger.info(f"         📅 {mov.get('fecha')} | {mov.get('tipo')} | {mov.get('estado')}")
                
                return True
            else:
                logger.error(f"❌ Error listando movimientos: {response.status_code}")
                logger.error(f"   Detalle: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en ejemplo de listado: {e}")
            return False
    
    def ejemplo_estadisticas_generales(self, empresa_id: int = 1):
        """
        Ejemplo 5: Obtener estadísticas generales
        """
        logger.info("\n" + "="*60)
        logger.info("📈 EJEMPLO 5: Estadísticas Generales")
        logger.info("="*60)
        
        try:
            logger.info(f"📈 Obteniendo estadísticas para empresa ID {empresa_id}...")
            
            response = self.session.get(f"{self.base_url}/estadisticas/{empresa_id}")
            
            if response.status_code == 200:
                stats = response.json()
                
                logger.info("✅ Estadísticas generales:")
                
                # Información de empresa
                empresa = stats.get('empresa', {})
                logger.info(f"   🏢 Empresa: {empresa.get('razon_social')}")
                logger.info(f"   🆔 RFC: {empresa.get('rfc')}")
                
                # Estadísticas de movimientos
                movimientos = stats.get('movimientos', {})
                logger.info(f"\n   💳 Movimientos:")
                logger.info(f"      - Total: {movimientos.get('total', 0)}")
                logger.info(f"      - Conciliados: {movimientos.get('conciliados', 0)}")
                logger.info(f"      - Pendientes: {movimientos.get('pendientes', 0)}")
                logger.info(f"      - Tasa conciliación: {movimientos.get('porcentaje_conciliacion', 0):.2f}%")
                logger.info(f"      - Monto total: ${movimientos.get('monto_total', 0):,.2f}")
                
                # Estadísticas de archivos
                archivos = stats.get('archivos', {})
                logger.info(f"\n   📁 Archivos procesados:")
                logger.info(f"      - Total: {archivos.get('total_procesados', 0)}")
                logger.info(f"      - Exitosos: {archivos.get('exitosos', 0)}")
                logger.info(f"      - Tasa éxito: {archivos.get('tasa_exito', 0):.2f}%")
                
                # Últimos procesos
                ultimos = stats.get('ultimos_procesos', [])
                if ultimos:
                    logger.info(f"\n   🕐 Últimos procesos:")
                    for proceso in ultimos:
                        logger.info(f"      - {proceso.get('periodo')}: {proceso.get('porcentaje', 0):.1f}% conciliado")
                
                return True
            else:
                logger.error(f"❌ Error obteniendo estadísticas: {response.status_code}")
                logger.error(f"   Detalle: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en ejemplo de estadísticas: {e}")
            return False
    
    def ejecutar_todos_los_ejemplos(self):
        """
        Ejecuta todos los ejemplos en secuencia
        """
        logger.info("\n" + "🚀"*30)
        logger.info("🚀 INICIANDO EJEMPLOS DEL MÓDULO DE CONCILIACIÓN BANCARIA")
        logger.info("🚀"*30)
        
        # Verificar servidor
        if not self.verificar_servidor():
            logger.error("💥 No se puede continuar sin conexión al servidor")
            return False
        
        # Mostrar endpoints
        self.mostrar_endpoints_disponibles()
        
        # Pausa para que el usuario pueda leer
        time.sleep(2)
        
        # Ejecutar ejemplos
        resultados = []
        
        # Ejemplo 1: Subir estado de cuenta
        archivo_id = self.ejemplo_subir_estado_cuenta()
        resultados.append(archivo_id is not None)
        
        time.sleep(1)
        
        # Ejemplo 2: Ejecutar conciliación
        resultado_conciliacion = self.ejemplo_ejecutar_conciliacion()
        resultados.append(resultado_conciliacion)
        
        time.sleep(1)
        
        # Ejemplo 3: Obtener reporte
        resultado_reporte = self.ejemplo_obtener_reporte()
        resultados.append(resultado_reporte)
        
        time.sleep(1)
        
        # Ejemplo 4: Listar movimientos
        resultado_movimientos = self.ejemplo_listar_movimientos()
        resultados.append(resultado_movimientos)
        
        time.sleep(1)
        
        # Ejemplo 5: Estadísticas generales
        resultado_estadisticas = self.ejemplo_estadisticas_generales()
        resultados.append(resultado_estadisticas)
        
        # Resumen final
        logger.info("\n" + "🎉"*30)
        logger.info("🎉 RESUMEN DE EJEMPLOS COMPLETADOS")
        logger.info("🎉"*30)
        
        ejemplos = [
            "Subir Estado de Cuenta",
            "Ejecutar Conciliación", 
            "Obtener Reporte",
            "Listar Movimientos",
            "Estadísticas Generales"
        ]
        
        exitosos = sum(resultados)
        total = len(resultados)
        
        for i, (ejemplo, resultado) in enumerate(zip(ejemplos, resultados)):
            estado = "✅" if resultado else "❌"
            logger.info(f"   {estado} {i+1}. {ejemplo}")
        
        logger.info(f"\n📊 Resultado final: {exitosos}/{total} ejemplos exitosos")
        
        if exitosos == total:
            logger.info("🎉 ¡Todos los ejemplos funcionaron correctamente!")
            logger.info("🔗 El módulo de conciliación bancaria está listo para usar")
        else:
            logger.warning("⚠️  Algunos ejemplos fallaron. Revisar configuración.")
        
        return exitosos == total


def main():
    """Función principal del ejemplo"""
    print("\n" + "="*80)
    print("🏦 EJEMPLO COMPLETO DEL MÓDULO DE CONCILIACIÓN BANCARIA AVANZADA")
    print("="*80)
    print("\nEste ejemplo demuestra todas las funcionalidades del módulo:")
    print("  1. 📤 Procesamiento OCR de estados de cuenta")
    print("  2. ⚡ Conciliación automática con 6 estrategias")
    print("  3. 📊 Generación de reportes detallados")
    print("  4. 📋 Gestión de movimientos bancarios")
    print("  5. 📈 Estadísticas y métricas de calidad")
    print("\n⚠️  NOTA: Asegúrate de tener:")
    print("   - El servidor FastAPI ejecutándose (puerto 8000)")
    print("   - OPENAI_API_KEY configurada en .env")
    print("   - Las tablas de base de datos creadas")
    print("\n¿Continuar? (presiona Enter)")
    input()
    
    # Crear instancia del ejemplo
    ejemplo = EjemploConciliacionBancaria()
    
    # Ejecutar todos los ejemplos
    exito = ejemplo.ejecutar_todos_los_ejemplos()
    
    if exito:
        print("\n🎊 ¡Felicidades! El módulo de conciliación está funcionando perfectamente.")
        print("🔗 Puedes ahora:")
        print("   - Visitar http://localhost:8000/docs para ver la documentación")
        print("   - Integrar el módulo en tu aplicación")
        print("   - Procesar estados de cuenta reales")
    else:
        print("\n😞 Algunos ejemplos fallaron. Revisa los logs para más detalles.")
    
    return exito


if __name__ == "__main__":
    main() 