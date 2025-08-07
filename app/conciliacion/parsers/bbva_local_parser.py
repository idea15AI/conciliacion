"""
Parser local para BBVA cuando el documento es muy grande.
Extrae movimientos a partir de líneas de tabla sin usar IA.
"""

import re
import time
import logging
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class BBVALocalParser:
    """Parser local para documentos BBVA grandes sin usar IA."""
    
    def __init__(self):
        pass
    
    def procesar_bbva_grande_local(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parser local para BBVA cuando el documento es muy grande.
        Extrae movimientos a partir de líneas de tabla sin usar IA.
        """
        inicio = time.time()
        try:
            doc = fitz.open(pdf_path)
            lineas: list[str] = []
            for page in doc:
                text = page.get_text()
                if not text:
                    continue
                for raw in text.splitlines():
                    s = " ".join(raw.strip().split())
                    if s:
                        lineas.append(s)
            doc.close()

            # Filtrar encabezados comunes
            encabezados = [
                'FECHA SALDO', 'OPER LIQ COD.', 'CARGOS ABONOS', 'OPERACIÓN LIQUIDACIÓN',
                'DETALLE DE MOVIMIENTOS'
            ]
            filtradas: list[str] = []
            for ln in lineas:
                up = ln.upper()
                if any(h in up for h in encabezados):
                    continue
                filtradas.append(ln)

            # Agrupar por bloques que empiezan con fecha tipo 30/MAY
            pat_fecha = re.compile(r"^(\d{2}/[A-ZÁÉÍÓÚÑ]{3})\b")
            pat_ref = re.compile(r"\bRef\.\s*([^\s]+)", re.IGNORECASE)
            pat_monto = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d{2})$")
            amount_token_pat = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b")
            pat_digits = re.compile(r"^[0-9]{10,}$")

            bloques: list[list[str]] = []
            actual: list[str] = []
            for ln in filtradas:
                if pat_fecha.match(ln):
                    if actual:
                        bloques.append(actual)
                    actual = [ln]
                else:
                    if actual:
                        actual.append(ln)
            if actual:
                bloques.append(actual)

            movimientos: list[Dict[str, Any]] = []
            vistos: set[str] = set()

            def parse_monto(s: str) -> float:
                return float(s.replace(',', ''))

            for blk in bloques:
                try:
                    primera = blk[0]
                    m = pat_fecha.match(primera)
                    if not m:
                        continue
                    fecha = m.group(1)
                    
                    # Texto completo del bloque (para detectar códigos como T20, T17, N06, AA7, C02)
                    bloque_texto_upper = (" ".join(blk)).upper()
                    op_code = None
                    try:
                        mcode = re.search(r"\b(T\d{2}|N\d{2}|AA\d|C\d{2})\b", bloque_texto_upper)
                        if mcode:
                            op_code = mcode.group(1)
                    except Exception:
                        op_code = None
                    
                    # Variables para el procesamiento del bloque
                    concepto_lines: list[str] = []
                    referencia = None
                    movimiento_monto: Optional[float] = None
                    saldo_movimiento: Optional[float] = None
                    oper_code = None  # Para capturar códigos como T20, N06, etc.
                    
                    stop_markers = [
                        'TOTAL DE MOVIMIENTOS', 'TOTAL IMPORTE CARGOS', 'TOTAL IMPORTE ABONOS',
                        'BBVA MEXICO', 'ESTADO DE CUENTA', 'PAGINA', 'GLOSARIO DE ABREVIATURAS',
                        'REGIMEN FISCAL', 'RÉGIMEN FISCAL', 'FOLIO FISCAL', 'CERTIFICADO', 'SELLO SAT',
                        'CADENA ORIGINAL', 'UNIDAD ESPECIALIZADA', 'POR DISPOSICION OFICIAL',
                        'POR DISPOSICIÓN OFICIAL', 'NO. CUENTA', 'NO. CLIENTE', 'CUADRO RESUMEN',
                        'GRAFICO DE MOVIMIENTOS', 'GRÁFICO DE MOVIMIENTOS'
                    ]
                    
                    for ln in blk[1:]:
                        refm = pat_ref.search(ln)
                        if refm:
                            # Usar solo el valor de la referencia, sin el prefijo "Ref."
                            referencia = refm.group(1).strip()
                        
                        clean_ln = ln.strip().replace(" ", "")
                        up_ln = ln.upper()
                        
                        # Si encontramos marcadores de resumen/legales, cortamos el bloque aquí
                        if any(marker in up_ln for marker in stop_markers):
                            break
                        
                        # Capturar código de operación (T20, N06, etc.) de la primera línea
                        if oper_code is None:
                            oper_match = re.search(r"\b(T\d{2}|N\d{2}|AA\d|C\d{2})\b", ln)
                            if oper_match:
                                oper_code = oper_match.group(1)
                        
                        # Capturar montos: PRIMER monto = movimiento, ÚLTIMO monto = saldo (liquidación)
                        try:
                            tokens = amount_token_pat.findall(ln)
                            if tokens:
                                if movimiento_monto is None:
                                    movimiento_monto = parse_monto(tokens[0])  # Primer monto = movimiento
                                # Último monto = saldo (liquidación) - solo si hay más de un monto
                                if len(tokens) > 1:
                                    saldo_movimiento = parse_monto(tokens[-1])
                        except Exception:
                            pass
                        
                        # Aceptar líneas que son solo monto (caso habitual en extracción)
                        if movimiento_monto is None and pat_monto.match(ln.strip()):
                            try:
                                movimiento_monto = parse_monto(ln.strip())
                                # Si solo hay un monto, no asignar saldo (queda null)
                            except Exception:
                                pass
                        
                        # Ignorar líneas que son solo dígitos largos (cuentas, rastreos)
                        if pat_digits.match(clean_ln):
                            continue
                        
                        # Agregar línea al concepto si no es solo monto y no es solo números
                        if not pat_monto.match(ln.strip()) and not pat_digits.match(clean_ln):
                            # Limpiar la línea antes de agregarla al concepto
                            clean_concept_line = ln.strip()
                            # Remover códigos de operación del concepto
                            clean_concept_line = re.sub(r"\b(T\d{2}|N\d{2}|AA\d|C\d{2})\b", "", clean_concept_line)
                            # Remover códigos BNET
                            clean_concept_line = re.sub(r"\bBNET\s+\d+\b", "", clean_concept_line)
                            # Limpiar espacios extra
                            clean_concept_line = " ".join(clean_concept_line.split())
                            if clean_concept_line:
                                concepto_lines.append(clean_concept_line)
                    
                    # Normalizar concepto
                    concepto = " ".join(concepto_lines).strip()
                    
                    # Recorte defensivo del concepto ante marcadores si se colaron
                    concepto_up = concepto.upper()
                    for marker in stop_markers:
                        idx = concepto_up.find(marker)
                        if idx != -1:
                            concepto = concepto[:idx].strip()
                            concepto_up = concepto.upper()
                            break
                    concepto_norm = " ".join(concepto.split())

                    # Heurística de cargo/abono mejorada
                    upper_concept = concepto.upper()
                    cargos = None
                    abonos = None
                    monto_detectado = movimiento_monto
                    
                    # 1) Reglas por código de operación (oper_code) - más específico
                    if oper_code == 'T20':
                        abonos = monto_detectado  # SPEI RECIBIDO
                    elif oper_code == 'T17':
                        cargos = monto_detectado  # SPEI ENVIADO
                    elif oper_code in ('AA7', 'C02'):
                        abonos = monto_detectado  # Depósito efectivo
                    elif oper_code and oper_code.startswith('N'):
                        # Nxx (e.g., N06 PAGO CUENTA DE TERCERO) depende del contexto
                        if 'PAGO CUENTA DE TERCERO' in upper_concept:
                            # Para N06, verificar si es envío o recepción
                            if any(k in upper_concept for k in ['ENVIADO', 'TRANSFERENCIA', 'PAGO', 'COMPRA', 'DEBITO', 'RETIRO', 'BNET']):
                                cargos = monto_detectado
                            else:
                                abonos = monto_detectado  # Por defecto, si no hay pistas claras
                    
                    # 2) Reglas por palabras clave fuertes si aún no decidido
                    if cargos is None and abonos is None:
                        if any(k in upper_concept for k in ['SPEI ENVIADO', 'ENVIADO', 'RETIRO', 'DEBITO', 'COMISION', 'TASA', 'IVA', 'ISR']):
                            cargos = monto_detectado
                        elif any(k in upper_concept for k in ['SPEI RECIBIDO', 'RECIBIDO', 'DEPOSITO EFECTIVO', 'DEPOSITO EN EFECTIVO', 'DEPOSITO', 'PRACTIC']):
                            abonos = monto_detectado
                    
                    # 3) Fallback final: usar código de operación como guía
                    if cargos is None and abonos is None:
                        if oper_code and oper_code.startswith('T'):
                            if oper_code == 'T20':
                                abonos = monto_detectado
                            elif oper_code == 'T17':
                                cargos = monto_detectado
                            else:
                                # Para otros códigos T, verificar contexto
                                if any(k in upper_concept for k in ['RECIBIDO', 'DEPOSITO']):
                                    abonos = monto_detectado
                                else:
                                    cargos = monto_detectado
                        else:
                            # Sin código de operación, usar contexto
                            if any(k in upper_concept for k in ['RECIBID', 'DEPOSITO', 'PRACTIC']):
                                abonos = monto_detectado
                            else:
                                cargos = monto_detectado

                    # Enforce exclusividad: no ambos
                    if cargos is not None and abonos is not None:
                        # Si ambos tienen valor, priorizar por código de operación
                        if oper_code == 'T20':
                            cargos = None
                        elif oper_code == 'T17':
                            abonos = None
                        else:
                            # Por contexto
                            if any(k in upper_concept for k in ['ENVIADO', 'PAGO CUENTA DE TERCERO', 'BNET']):
                                abonos = None
                            elif any(k in upper_concept for k in ['RECIBIDO', 'DEPOSITO']):
                                cargos = None
                            else:
                                # Por defecto, mantener cargo
                                abonos = None

                    # Validaciones mínimas
                    if not monto_detectado or (cargos is None and abonos is None):
                        continue

                    # Logging detallado para debugging
                    logger.info(f"🔍 Movimiento procesado: fecha={fecha}, oper_code={oper_code}, concepto={concepto[:50]}, monto={monto_detectado}, cargos={cargos}, abonos={abonos}, saldo={saldo_movimiento}")

                    mov = {
                        'fecha': fecha,
                        'concepto': concepto if concepto else 'SIN DESCRIPCION',
                        'referencia': referencia,
                        'cargos': cargos,
                        'abonos': abonos,
                        'saldo': saldo_movimiento
                    }

                    # Deduplicación por (fecha, ref, monto, concepto recortado)
                    key = f"{mov['fecha']}|{mov.get('referencia') or ''}|{round(monto_detectado or 0.0, 2)}|{concepto_norm[:80].upper()}"
                    if key in vistos:
                        continue
                    vistos.add(key)
                    movimientos.append(mov)
                except Exception as e:
                    logger.warning(f"⚠️ Error procesando bloque en parser local BBVA: {e} - Bloque: {blk}")
                    continue

            logger.info(f"🧹 Parser local BBVA: {len(movimientos)} movimientos tras limpieza")
            return {
                'exito': True,
                'mensaje': f"Parser local BBVA: {len(movimientos)} movimientos",
                'banco_detectado': 'BBVA',
                'periodo_detectado': None,
                'total_movimientos_extraidos': len(movimientos),
                'movimientos': movimientos,
                'modelo_utilizado': 'local-parser',
                'tiempo_procesamiento_segundos': round(time.time() - inicio, 2),
                'errores': []
            }
        except Exception as e:
            logger.error(f"❌ Error en parser local BBVA: {e}")
            return {
                'exito': False,
                'mensaje': f"Error parser local BBVA: {e}",
                'banco_detectado': 'BBVA',
                'periodo_detectado': None,
                'total_movimientos_extraidos': 0,
                'movimientos': [],
                'modelo_utilizado': 'local-parser',
                'tiempo_procesamiento_segundos': round(time.time() - inicio, 2),
                'errores': [str(e)]
            } 