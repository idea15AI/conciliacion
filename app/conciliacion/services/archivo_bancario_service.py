
import hashlib
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.conciliacion.models import ArchivoBancario, TipoBanco, MovimientoBancario, TipoMovimiento, EstadoConciliacion
from app.conciliacion.gemini_processor import GeminiProcessor
from app.core.database import get_db
from app.models.mysql_models import EmpresaContribuyente

logger = logging.getLogger(__name__)


class ArchivoBancarioService:
    #Servicio para gestión completa de archivos bancarios
    
    def __init__(self, db: Session):
        #Inicializa el servicio con una sesión de BD
        self.db = db
        self.gemini_processor = GeminiProcessor()
    
    def verificar_empresa_existe(self, empresa_id: int) -> bool:
        #Verifica si la empresa existe en la base de datos
        try:
            empresa = self.db.query(EmpresaContribuyente).filter(
                EmpresaContribuyente.id == empresa_id
            ).first()
            
            if empresa:
                logger.info(f"✅ Empresa encontrada: {empresa.razon_social} (ID: {empresa_id})")
                return True
            else:
                logger.warning(f"⚠️ Empresa no encontrada: ID {empresa_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando empresa: {e}")
            return False
    
    def calcular_hash_archivo(self, file_path: str) -> str:
        #Calcula el hash SHA-256 de un archivo
        try:
            hash_sha256 = hashlib.sha256()
            
            with open(file_path, 'rb') as f:
                # Leer archivo en chunks para eficiencia
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            
            return hash_sha256.hexdigest()
            
        except FileNotFoundError:
            logger.error(f"❌ Archivo no encontrado: {file_path}")
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        except IOError as e:
            logger.error(f"❌ Error leyendo archivo {file_path}: {e}")
            raise IOError(f"Error leyendo archivo: {e}")
    
    def verificar_duplicado(self, hash_archivo: str, empresa_id: int) -> Optional[ArchivoBancario]:
        #Verifica si ya existe un archivo con el mismo hash para la empresa
        try:
            archivo_existente = self.db.query(ArchivoBancario).filter(
                ArchivoBancario.hash_archivo == hash_archivo,
                ArchivoBancario.empresa_id == empresa_id
            ).first()
            
            if archivo_existente:
                logger.warning(f"⚠️ Archivo duplicado detectado: {archivo_existente.nombre_archivo}")
                return archivo_existente
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error verificando duplicado: {e}")
            raise
    
    def verificar_y_crear_archivo_bancario(self, 
                                          empresa_id: int,
                                          nombre_archivo: str,
                                          file_path: str,
                                          tamano_bytes: int) -> Tuple[ArchivoBancario, bool]:
        #Verifica si existe un archivo con el mismo hash y crea uno nuevo si no existe
        try:
            # Verificar que la empresa existe
            if not self.verificar_empresa_existe(empresa_id):
                raise ValueError(f"Empresa con ID {empresa_id} no existe")
            
            # Calcular hash del archivo
            hash_archivo = self.calcular_hash_archivo(file_path)
            logger.info(f"🔐 Hash calculado: {hash_archivo[:16]}...")
            
            # Verificar si ya existe un archivo con este hash
            archivo_existente = self.verificar_duplicado(hash_archivo, empresa_id)
            
            if archivo_existente:
                logger.info(f"✅ Archivo ya existe: {archivo_existente.nombre_archivo} (ID: {archivo_existente.id})")
                return archivo_existente, False
            
            # Si no existe, crear nuevo registro
            logger.info(f"🆕 Creando nuevo archivo: {nombre_archivo}")
            
            archivo_bancario = ArchivoBancario(
                empresa_id=empresa_id,
                nombre_archivo=nombre_archivo,
                hash_archivo=hash_archivo,
                tamano_bytes=tamano_bytes,
                banco=TipoBanco.OTRO,  # Se detectará durante el procesamiento
                procesado_exitosamente=False,
                fecha_creacion=datetime.now()
            )
            
            self.db.add(archivo_bancario)
            self.db.commit()
            self.db.refresh(archivo_bancario)
            
            logger.info(f"✅ Archivo bancario creado: ID {archivo_bancario.id}")
            return archivo_bancario, True
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"❌ Error de integridad en BD: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error creando archivo bancario: {e}")
            raise
    
    def procesar_archivo(self, archivo_bancario: ArchivoBancario, file_path: str) -> Dict[str, Any]:
        #Procesa un archivo bancario con Gemini y actualiza la BD
        inicio_procesamiento = datetime.now()
        
        try:
            logger.info(f"🚀 Iniciando procesamiento: {archivo_bancario.nombre_archivo}")
            
            # Procesar con Gemini
            resultado = self.gemini_processor.procesar_pdf(file_path)
            
            # Actualizar archivo con resultados
            self._actualizar_archivo_con_resultados(archivo_bancario, resultado, inicio_procesamiento)
            
            logger.info(f"✅ Procesamiento completado: {resultado.get('total_movimientos_extraidos', 0)} movimientos")
            return resultado
            
        except Exception as e:
            # Actualizar archivo con error
            self._actualizar_archivo_con_error(archivo_bancario, str(e), inicio_procesamiento)
            logger.error(f"❌ Error procesando archivo: {e}")
            raise
    
    def _actualizar_archivo_con_resultados(self, 
                                         archivo_bancario: ArchivoBancario,
                                         resultado: Dict[str, Any],
                                         inicio_procesamiento: datetime) -> None:
        #Actualiza el archivo bancario con los resultados del procesamiento
        try:
            # Extraer datos del resultado
            banco_detectado = resultado.get('banco_detectado', 'OTRO')
            movimientos = resultado.get('movimientos', [])
            tiempo_procesamiento = resultado.get('tiempo_procesamiento_segundos', 0)
            
            # Actualizar campos del archivo
            archivo_bancario.banco = self._mapear_banco(banco_detectado)
            archivo_bancario.total_movimientos = len(movimientos)
            archivo_bancario.movimientos_procesados = len(movimientos)
            archivo_bancario.tiempo_procesamiento = int(tiempo_procesamiento)
            archivo_bancario.procesado_exitosamente = resultado.get('exito', False)
            archivo_bancario.fecha_procesamiento = datetime.now()
            
            # Extraer información adicional si está disponible
            if movimientos:
                # Extraer saldos inicial y final de manera más inteligente
                self._extraer_saldos_periodo(archivo_bancario, movimientos)
                
                # Guardar movimientos en la base de datos
                movimientos_guardados = self._guardar_movimientos_bd(archivo_bancario, movimientos)
                archivo_bancario.movimientos_procesados = movimientos_guardados
                
                # Intentar extraer fechas de periodo
                fechas = [m.get('fecha') for m in movimientos if m.get('fecha')]
                if fechas:
                    try:
                        fechas_parsed = [datetime.strptime(f, '%d/%m/%Y') for f in fechas if f]
                        if fechas_parsed:
                            archivo_bancario.periodo_inicio = min(fechas_parsed)
                            archivo_bancario.periodo_fin = max(fechas_parsed)
                    except ValueError:
                        logger.warning("⚠️ No se pudieron parsear las fechas del periodo")
            
            # Guardar metadatos adicionales
            archivo_bancario.datos_metadata = {
                'modelo_utilizado': resultado.get('modelo_utilizado'),
                'banco_detectado': banco_detectado,
                'errores': resultado.get('errores', []),
                'tiempo_procesamiento_segundos': tiempo_procesamiento
            }
            
            self.db.commit()
            logger.info(f"✅ Archivo actualizado: {archivo_bancario.nombre_archivo}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error actualizando archivo: {e}")
            raise
    
    def _actualizar_archivo_con_error(self, 
                                     archivo_bancario: ArchivoBancario,
                                     error_msg: str,
                                     inicio_procesamiento: datetime) -> None:
        #Actualiza el archivo bancario con información de error
        try:
            tiempo_procesamiento = (datetime.now() - inicio_procesamiento).total_seconds()
            
            archivo_bancario.procesado_exitosamente = False
            archivo_bancario.fecha_procesamiento = datetime.now()
            archivo_bancario.tiempo_procesamiento = int(tiempo_procesamiento)
            archivo_bancario.errores_ocr = [error_msg]
            
            self.db.commit()
            logger.info(f"❌ Archivo marcado como fallido: {archivo_bancario.nombre_archivo}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error actualizando archivo con error: {e}")
    
    def _extraer_saldos_periodo(self, archivo_bancario: ArchivoBancario, movimientos: List[Dict[str, Any]]) -> None:
        #Extrae saldo inicial y final de los movimientos de manera inteligente
        try:
            # Filtrar movimientos con saldos válidos (no None, no 0)
            saldos_validos = []
            for mov in movimientos:
                saldo = mov.get('saldo')
                if saldo is not None and saldo != 0:
                    saldos_validos.append(saldo)
            
            if saldos_validos:
                # Usar el primer y último saldo válido
                archivo_bancario.saldo_inicial = saldos_validos[0]
                archivo_bancario.saldo_final = saldos_validos[-1]
                logger.info(f"💰 Saldos extraídos: Inicial=${archivo_bancario.saldo_inicial}, Final=${archivo_bancario.saldo_final}")
            else:
                # Intentar calcular saldos basándose en cargos y abonos
                self._calcular_saldos_por_movimientos(archivo_bancario, movimientos)
                
        except Exception as e:
            logger.warning(f"⚠️ Error extrayendo saldos: {e}")
    
    def _calcular_saldos_por_movimientos(self, archivo_bancario: ArchivoBancario, movimientos: List[Dict[str, Any]]) -> None:
        #Calcula saldos basándose en los movimientos si no están disponibles
        try:
            saldo_actual = 0.0
            
            for mov in movimientos:
                cargos = mov.get('cargos', 0) or 0
                abonos = mov.get('abonos', 0) or 0
                
                # Calcular saldo después del movimiento
                saldo_actual += abonos - cargos
                
                # Si el movimiento tiene saldo explícito, usarlo
                saldo_mov = mov.get('saldo')
                if saldo_mov is not None and saldo_mov != 0:
                    saldo_actual = saldo_mov
            
            # Si calculamos saldos, usar el primer movimiento como inicial
            if movimientos:
                primer_mov = movimientos[0]
                cargos_inicial = primer_mov.get('cargos', 0) or 0
                abonos_inicial = primer_mov.get('abonos', 0) or 0
                
                archivo_bancario.saldo_inicial = saldo_actual - abonos_inicial + cargos_inicial
                archivo_bancario.saldo_final = saldo_actual
                
                logger.info(f"💰 Saldos calculados: Inicial=${archivo_bancario.saldo_inicial}, Final=${archivo_bancario.saldo_final}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error calculando saldos: {e}")
    
    def _guardar_movimientos_bd(self, archivo_bancario: ArchivoBancario, movimientos: List[Dict[str, Any]]) -> int:
        #Guarda los movimientos extraídos en la base de datos
        try:
            movimientos_guardados = 0
            
            for mov in movimientos:
                try:
                    # Parsear fecha
                    fecha_str = mov.get('fecha')
                    if not fecha_str:
                        logger.warning(f"⚠️ Movimiento sin fecha, saltando: {mov}")
                        continue
                    
                    # Intentar diferentes formatos de fecha
                    fecha = None
                    for formato in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']:
                        try:
                            fecha = datetime.strptime(fecha_str, formato)
                            break
                        except ValueError:
                            continue
                    
                    if not fecha:
                        logger.warning(f"⚠️ No se pudo parsear fecha '{fecha_str}', usando fecha actual")
                        fecha = datetime.now()
                    
                    # Determinar tipo de movimiento y monto
                    cargos = mov.get('cargos')
                    abonos = mov.get('abonos')
                    
                    # Inicializar como None
                    tipo_movimiento = None
                    monto = None
                    
                    # Determinar tipo y monto basándose en cargos y abonos
                    if cargos is not None and cargos > 0:
                        tipo_movimiento = TipoMovimiento.CARGO
                        monto = cargos
                    elif abonos is not None and abonos > 0:
                        tipo_movimiento = TipoMovimiento.ABONO
                        monto = abonos
                    else:
                        # Si no hay cargos ni abonos válidos, intentar determinar por concepto
                        concepto = mov.get('concepto', '').lower()
                        saldo = mov.get('saldo')
                        
                        if any(palabra in concepto for palabra in ['cargo', 'retiro', 'pago', 'debito', 'cobro']):
                            tipo_movimiento = TipoMovimiento.CARGO
                            monto = saldo if saldo is not None else None
                        elif any(palabra in concepto for palabra in ['abono', 'deposito', 'ingreso', 'transferencia']):
                            tipo_movimiento = TipoMovimiento.ABONO
                            monto = saldo if saldo is not None else None
                        else:
                            # Si no se puede determinar, usar ABONO como valor por defecto
                            # pero mantener monto como None si no hay saldo
                            tipo_movimiento = TipoMovimiento.ABONO
                            monto = saldo if saldo is not None else None
                    
                    # Crear movimiento bancario
                    # Usar 0.0 como valor por defecto para monto si es None
                    monto_final = monto if monto is not None else 0.0
                    
                    movimiento = MovimientoBancario(
                        empresa_id=archivo_bancario.empresa_id,
                        fecha=fecha,
                        concepto=mov.get('concepto', 'Sin concepto'),
                        monto=monto_final,
                        tipo=tipo_movimiento,  # Ahora siempre tiene un valor (CARGO o ABONO)
                        referencia=mov.get('referencia'),
                        saldo=mov.get('saldo'),
                        estado=EstadoConciliacion.PENDIENTE,
                        archivo_origen_id=archivo_bancario.id,
                        datos_ocr={
                            'tipo_raw': str(tipo_movimiento.value),
                            'fecha_raw': fecha_str,
                            'monto_raw': str(monto) if monto is not None else 'null',
                            'concepto_raw': mov.get('concepto', ''),
                            'procesado_en': datetime.now().isoformat()
                        },
                        fecha_creacion=datetime.now()
                    )
                    
                    self.db.add(movimiento)
                    movimientos_guardados += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error guardando movimiento: {e}")
                    continue
            
            # Commit de todos los movimientos
            self.db.commit()
            logger.info(f"✅ Guardados {movimientos_guardados} movimientos en BD")
            
            return movimientos_guardados
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error guardando movimientos: {e}")
            return 0
    
    def _mapear_banco(self, banco_detectado: str) -> TipoBanco:
        #Mapea el banco detectado por Gemini al enum TipoBanco
        banco_upper = banco_detectado.upper()
        
        mapeo = {
            'BANORTE': TipoBanco.BANORTE,
            'SANTANDER': TipoBanco.SANTANDER,
            'BBVA': TipoBanco.BBVA,
            'INBURSA': TipoBanco.INBURSA,
            'BANAMEX': TipoBanco.BANAMEX,
            'HSBC': TipoBanco.HSBC,
            'SCOTIABANK': TipoBanco.SCOTIABANK,
            'AZTECA': TipoBanco.AZTECA,
            'BANCO DEL BAJÍO': TipoBanco.OTRO,  # Agregar cuando se soporte
        }
        
        return mapeo.get(banco_upper, TipoBanco.OTRO)
    
    def obtener_archivos_empresa(self, empresa_id: int, limit: int = 50, offset: int = 0) -> List[ArchivoBancario]:
        #Obtiene los archivos bancarios de una empresa
        try:
            archivos = self.db.query(ArchivoBancario).filter(
                ArchivoBancario.empresa_id == empresa_id
            ).order_by(
                ArchivoBancario.fecha_creacion.desc()
            ).offset(offset).limit(limit).all()
            
            return archivos
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo archivos de empresa {empresa_id}: {e}")
            raise
    
    def obtener_archivo_por_id(self, archivo_id: int) -> Optional[ArchivoBancario]:
        #Obtiene un archivo bancario por ID
        try:
            return self.db.query(ArchivoBancario).filter(
                ArchivoBancario.id == archivo_id
            ).first()
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo archivo {archivo_id}: {e}")
            raise
    
    def eliminar_archivo(self, archivo_id: int) -> bool:
        #Elimina un archivo bancario
        try:
            archivo = self.obtener_archivo_por_id(archivo_id)
            if not archivo:
                return False
            
            self.db.delete(archivo)
            self.db.commit()
            
            logger.info(f"🗑️ Archivo eliminado: {archivo.nombre_archivo}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error eliminando archivo {archivo_id}: {e}")
            raise 