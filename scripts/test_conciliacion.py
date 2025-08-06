#!/usr/bin/env python3
"""
Script de prueba para Conciliación Mejorada con FuzzyWuzzy
Demuestra el enfoque de 3 pasos: exacto, fuzzy, manual
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.conciliacion.models import MovimientoBancario, EstadoConciliacion
from app.conciliacion.conciliador import ConciliadorMejorado, TipoConciliacion
from app.models.mysql_models import ComprobanteFiscal

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def instalar_fuzzywuzzy():
    """Instala FuzzyWuzzy si no está disponible"""
    try:
        import fuzzywuzzy
        logger.info("✅ FuzzyWuzzy ya está instalado")
        return True
    except ImportError:
        logger.info("📦 Instalando FuzzyWuzzy...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "fuzzywuzzy", "python-Levenshtein"])
            logger.info("✅ FuzzyWuzzy instalado correctamente")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error instalando FuzzyWuzzy: {e}")
            return False

def probar_conciliacion_mejorada(empresa_id: int = 1):
    """
    Prueba el conciliador mejorado con datos reales
    """
    logger.info(f"🚀 Iniciando prueba de conciliación para empresa {empresa_id}")
    
    # Obtener sesión de BD
    db = next(get_db())
    
    try:
        # Verificar que existan movimientos bancarios
        movimientos = db.query(MovimientoBancario).filter(
            MovimientoBancario.empresa_id == empresa_id
        ).all()
        
        if not movimientos:
            logger.warning(f"⚠️ No se encontraron movimientos para empresa {empresa_id}")
            return
        
        logger.info(f"📊 Encontrados {len(movimientos)} movimientos para conciliar")
        
        # Verificar que existan CFDIs
        cfdis = db.query(ComprobanteFiscal).filter(
            ComprobanteFiscal.empresa_id == empresa_id
        ).all()
        
        if not cfdis:
            logger.warning(f"⚠️ No se encontraron CFDIs para empresa {empresa_id}")
            return
        
        logger.info(f"📄 Encontrados {len(cfdis)} CFDIs para comparar")
        
        # Crear conciliador
        conciliador = ConciliadorMejorado(db, empresa_id)
        conciliador.umbral_fuzzy = 80  # Umbral más permisivo para prueba
        
        # Ejecutar conciliación
        logger.info("🔍 Ejecutando conciliación...")
        resultados = conciliador.conciliar_movimientos(movimientos)
        
        # Generar reporte
        reporte = conciliador.generar_reporte(resultados)
        
        # Mostrar resultados
        logger.info("📋 RESULTADOS DE CONCILIACIÓN:")
        logger.info(f"   Total movimientos: {reporte['resumen']['total_movimientos']}")
        logger.info(f"   ✅ Conciliados exactos: {reporte['resumen']['conciliados_exactos']}")
        logger.info(f"   🧩 Conciliados fuzzy: {reporte['resumen']['conciliados_fuzzy']}")
        logger.info(f"   ⏳ Pendientes revisión: {reporte['resumen']['pendientes_revision']}")
        logger.info(f"   📊 Porcentaje automatizado: {reporte['resumen']['porcentaje_automatizado']:.1f}%")
        
        # Mostrar algunos detalles
        logger.info("\n🔍 DETALLES DE CONCILIACIÓN:")
        for detalle in reporte['detalles'][:5]:  # Solo primeros 5
            logger.info(f"   Movimiento {detalle['movimiento_id']}: {detalle['tipo']} - {detalle['razon']}")
        
        if len(reporte['detalles']) > 5:
            logger.info(f"   ... y {len(reporte['detalles']) - 5} más")
        
        return reporte
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de conciliación: {e}")
        return None
    finally:
        db.close()

def probar_fuzzy_matching():
    """
    Prueba específica de FuzzyWuzzy con ejemplos
    """
    logger.info("🧪 Probando FuzzyWuzzy con ejemplos...")
    
    try:
        from fuzzywuzzy import fuzz
        
        # Ejemplos de conceptos bancarios vs CFDIs
        ejemplos = [
            {
                "concepto_bancario": "PAGO FACTURA 001-ABC-123",
                "folio_cfdi": "001-ABC-123",
                "descripcion": "Coincidencia perfecta"
            },
            {
                "concepto_bancario": "SPEI RECIBIDO BANORTE 020502020 folios ref 0175802608",
                "folio_cfdi": "0175802608",
                "descripcion": "Referencia en texto largo"
            },
            {
                "concepto_bancario": "DEPOSITO EFECTIVO",
                "nombre_emisor": "DEPOSITO EFECTIVO S.A.",
                "descripcion": "Nombre similar"
            },
            {
                "concepto_bancario": "TRANSFERENCIA SPEI",
                "uuid": "A93CBB69-8945-453F-9DA2-56884C3B9A7B",
                "descripcion": "UUID en referencia"
            }
        ]
        
        for ejemplo in ejemplos:
            concepto = ejemplo["concepto_bancario"]
            
            # Probar con diferentes campos
            for campo, valor in ejemplo.items():
                if campo in ["concepto_bancario", "descripcion"]:
                    continue
                    
                puntaje = fuzz.partial_ratio(concepto.lower(), valor.lower())
                logger.info(f"   {concepto} vs {valor}: {puntaje}%")
        
        logger.info("✅ Pruebas de FuzzyWuzzy completadas")
        
    except Exception as e:
        logger.error(f"❌ Error en pruebas de FuzzyWuzzy: {e}")

def main():
    """
    Función principal
    """
    logger.info("🎯 INICIANDO PRUEBAS DE CONCILIACIÓN MEJORADA")
    
    # Instalar FuzzyWuzzy si es necesario
    if not instalar_fuzzywuzzy():
        logger.error("❌ No se pudo instalar FuzzyWuzzy. Abortando.")
        return
    
    # Probar FuzzyWuzzy
    probar_fuzzy_matching()
    
    # Probar conciliación completa
    reporte = probar_conciliacion_mejorada(empresa_id=1)
    
    if reporte:
        logger.info("✅ Pruebas completadas exitosamente")
    else:
        logger.warning("⚠️ Pruebas completadas con advertencias")

if __name__ == "__main__":
    main() 