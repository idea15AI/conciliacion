"""
Conciliador Mejorado con FuzzyWuzzy
Implementa el enfoque de 3 pasos: exacto, fuzzy, manual
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from app.models.mysql_models import ComprobanteFiscal, DocumentoRelacionadoPago, ComplementoPago
from app.conciliacion.models import MovimientoBancario, TipoMovimiento, EstadoConciliacion

logger = logging.getLogger(__name__)

class TipoConciliacion(Enum):
    EXACTA = "exacta"
    FUZZY = "fuzzy"
    PENDIENTE = "pendiente"

@dataclass
class ResultadoConciliacion:
    movimiento_id: int
    cfdi_id: Optional[int]
    tipo_conciliacion: TipoConciliacion
    puntaje_fuzzy: Optional[float] = None
    razon: str = ""
    fecha_conciliacion: datetime = None

class ConciliadorMejorado:
    """
    Conciliador que implementa el enfoque de 3 pasos:
    1. Filtro Estricto: Coincidencia Exacta
    2. Filtro Flexible: Fuzzy Matching
    3. Clasificación para Revisión Manual
    """
    
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.umbral_fuzzy = 85  # Umbral fijo en 85%
        self.ventana_dias = 7   # Búsqueda ±7 días
        
    def conciliar_movimientos(self, movimientos: List[MovimientoBancario]) -> List[ResultadoConciliacion]:
        """
        Proceso principal de conciliación con 3 pasos
        """
        resultados = []
        
        for movimiento in movimientos:
            logger.info(f"🔍 Conciliando movimiento {movimiento.id}: {movimiento.concepto}")
            
            # Paso 1: Búsqueda Exacta
            resultado_exacto = self._buscar_coincidencia_exacta(movimiento)
            if resultado_exacto:
                resultados.append(resultado_exacto)
                continue
                
            # Paso 2: Búsqueda Fuzzy
            resultado_fuzzy = self._buscar_coincidencia_fuzzy(movimiento)
            if resultado_fuzzy:
                resultados.append(resultado_fuzzy)
                continue
                
            # Paso 3: Marcar como Pendiente
            resultado_pendiente = ResultadoConciliacion(
                movimiento_id=movimiento.id,
                cfdi_id=None,
                tipo_conciliacion=TipoConciliacion.PENDIENTE,
                razon="No se encontró coincidencia automática",
                fecha_conciliacion=datetime.now()
            )
            resultados.append(resultado_pendiente)
            
        return resultados
    
    def _buscar_coincidencia_exacta(self, movimiento: MovimientoBancario) -> Optional[ResultadoConciliacion]:
        """
        Paso 1: Filtro Estricto - Coincidencia Exacta
        Busca CFDI con fecha y monto exactos
        """
        fecha_inicio = movimiento.fecha - timedelta(days=1)
        fecha_fin = movimiento.fecha + timedelta(days=1)
        
        # Buscar CFDIs en el rango de fechas
        cfdis = self.db.query(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == self.empresa_id,
                ComprobanteFiscal.fecha.between(fecha_inicio, fecha_fin),
                ComprobanteFiscal.estatus_sat == True
            )
        ).all()
        
        # Filtrar CFDIs válidos
        cfdis_validos = self._filtrar_cfdis_validos(cfdis)
        
        for cfdi in cfdis_validos:
            # Coincidencia exacta de monto
            if abs(cfdi.total - movimiento.monto) < 0.01:  # Tolerancia de 1 centavo
                return ResultadoConciliacion(
                    movimiento_id=movimiento.id,
                    cfdi_id=cfdi.id,
                    tipo_conciliacion=TipoConciliacion.EXACTA,
                    razon=f"Coincidencia exacta: CFDI {cfdi.uuid} - Monto: ${cfdi.total}",
                    fecha_conciliacion=datetime.now()
                )
        
        return None
    
    def _filtrar_cfdis_validos(self, cfdis: List[ComprobanteFiscal]) -> List[ComprobanteFiscal]:
        """
        Filtra CFDIs válidos para conciliación:
        - Ignora CFDIs de PPD (pago en parcialidades o diferido)
        - Solo CFDIs tipo 'I' (Ingreso) con método de pago 'PUE'
        - O CFDIs tipo 'P' (Pago) electrónicos
        """
        cfdis_validos = []
        
        for cfdi in cfdis:
            # Ignorar CFDIs de PPD (pago en parcialidades o diferido)
            if cfdi.metodo_pago == 'PPD':
                continue
                
            # Solo CFDIs tipo 'I' (Ingreso) con método de pago 'PUE'
            if cfdi.tipo_comprobante == 'I' and cfdi.metodo_pago == 'PUE':
                cfdis_validos.append(cfdi)
            # O CFDIs tipo 'P' (Pago) electrónicos
            elif cfdi.tipo_comprobante == 'P':
                cfdis_validos.append(cfdi)
        
        return cfdis_validos
    
    def _buscar_coincidencia_fuzzy(self, movimiento: MovimientoBancario) -> Optional[ResultadoConciliacion]:
        """
        Paso 2: Filtro Flexible - Fuzzy Matching
        Usa FuzzyWuzzy para encontrar coincidencias probables
        """
        fecha_inicio = movimiento.fecha - timedelta(days=self.ventana_dias)
        fecha_fin = movimiento.fecha + timedelta(days=self.ventana_dias)
        
        # Obtener CFDIs del período
        cfdis = self.db.query(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == self.empresa_id,
                ComprobanteFiscal.fecha.between(fecha_inicio, fecha_fin),
                ComprobanteFiscal.estatus_sat == True
            )
        ).all()
        
        # Filtrar CFDIs válidos
        cfdis_validos = self._filtrar_cfdis_validos(cfdis)
        
        if not cfdis_validos:
            return None
        
        # Preparar textos para comparación
        texto_movimiento = self._normalizar_texto(movimiento.concepto)
        mejores_coincidencias = []
        
        for cfdi in cfdis_validos:
            # Comparar con diferentes campos del CFDI
            textos_cfdi = [
                cfdi.serie_cfdi or "",
                cfdi.folio_cfdi or "",
                cfdi.nombre_emisor or "",
                cfdi.nombre_receptor or "",
                cfdi.uuid or ""
            ]
            
            for texto_cfdi in textos_cfdi:
                if not texto_cfdi:
                    continue
                    
                texto_cfdi_norm = self._normalizar_texto(texto_cfdi)
                
                # Usar partial_ratio para subcadenas (mejor para referencias)
                puntaje = fuzz.partial_ratio(texto_movimiento, texto_cfdi_norm)
                
                if puntaje >= self.umbral_fuzzy:
                    mejores_coincidencias.append({
                        'cfdi': cfdi,
                        'puntaje': puntaje,
                        'texto_comparado': texto_cfdi_norm
                    })
        
        # Tomar la mejor coincidencia
        if mejores_coincidencias:
            mejor = max(mejores_coincidencias, key=lambda x: x['puntaje'])
            
            return ResultadoConciliacion(
                movimiento_id=movimiento.id,
                cfdi_id=mejor['cfdi'].id,
                tipo_conciliacion=TipoConciliacion.FUZZY,
                puntaje_fuzzy=mejor['puntaje'],
                razon=f"Coincidencia fuzzy ({mejor['puntaje']}%): CFDI {mejor['cfdi'].uuid} - Texto: {mejor['texto_comparado']}",
                fecha_conciliacion=datetime.now()
            )
        
        return None
    
    def _normalizar_texto(self, texto: str) -> str:
        """
        Normaliza texto para mejor comparación fuzzy
        """
        if not texto:
            return ""
        
        # Convertir a minúsculas
        texto = texto.lower()
        
        # Remover caracteres especiales comunes
        caracteres_especiales = ['-', '_', '.', ',', '(', ')', '[', ']']
        for char in caracteres_especiales:
            texto = texto.replace(char, ' ')
        
        # Remover espacios múltiples
        texto = ' '.join(texto.split())
        
        return texto
    
    def _buscar_complementos_pago(self, movimiento: MovimientoBancario) -> Optional[ResultadoConciliacion]:
        """
        Búsqueda especial para complementos de pago (PPD)
        """
        fecha_inicio = movimiento.fecha - timedelta(days=self.ventana_dias)
        fecha_fin = movimiento.fecha + timedelta(days=self.ventana_dias)
        
        # Buscar complementos de pago
        complementos = self.db.query(ComplementoPago).join(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == self.empresa_id,
                ComprobanteFiscal.fecha.between(fecha_inicio, fecha_fin),
                ComprobanteFiscal.estatus_sat == True
            )
        ).all()
        
        for complemento in complementos:
            if abs(complemento.monto_pago - movimiento.monto) < 0.01:
                return ResultadoConciliacion(
                    movimiento_id=movimiento.id,
                    cfdi_id=complemento.cfdi_id,
                    tipo_conciliacion=TipoConciliacion.EXACTA,
                    razon=f"Complemento de pago: Monto ${complemento.monto_pago}",
                    fecha_conciliacion=datetime.now()
                )
        
        return None
    
    def generar_reporte(self, resultados: List[ResultadoConciliacion]) -> Dict:
        """
        Genera reporte de conciliación
        """
        total_movimientos = len(resultados)
        exactos = len([r for r in resultados if r.tipo_conciliacion == TipoConciliacion.EXACTA])
        fuzzy = len([r for r in resultados if r.tipo_conciliacion == TipoConciliacion.FUZZY])
        pendientes = len([r for r in resultados if r.tipo_conciliacion == TipoConciliacion.PENDIENTE])
        
        return {
            'resumen': {
                'total_movimientos': total_movimientos,
                'conciliados_exactos': exactos,
                'conciliados_fuzzy': fuzzy,
                'pendientes_revision': pendientes,
                'porcentaje_automatizado': ((exactos + fuzzy) / total_movimientos * 100) if total_movimientos > 0 else 0
            },
            'detalles': [
                {
                    'movimiento_id': r.movimiento_id,
                    'cfdi_id': r.cfdi_id,
                    'tipo': r.tipo_conciliacion.value,
                    'puntaje_fuzzy': r.puntaje_fuzzy,
                    'razon': r.razon
                }
                for r in resultados
            ]
        } 