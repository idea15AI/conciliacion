"""
Procesador OCR avanzado para estados de cuenta bancarios

Utiliza OpenAI Vision API (gpt-4o) para extraer información de estados de cuenta
bancarios mexicanos con máxima precisión y soporte para múltiples bancos.
"""

import io
import os
import time
import base64
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal
import json

try:
    import fitz  # PyMuPDF
    from PIL import Image
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()  # Cargar variables de entorno
except ImportError as e:
    raise ImportError(f"Dependencias faltantes: {e}. Instalar con: uv add PyMuPDF pillow openai python-dotenv")

from .exceptions import (
    OCRError, PDFProcessingError, BancoNoReconocidoError, 
    FormatoBancarioInvalidoError, handle_openai_error, ExternalServiceError
)
from .models import TipoBanco, TipoMovimiento
from .utils import calcular_hash_archivo, extraer_numeros, normalizar_texto

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    Procesador OCR avanzado para estados de cuenta bancarios mexicanos
    
    Características:
    - Detección automática de banco
    - Extracción inteligente de movimientos
    - Validación y limpieza de datos
    - Manejo robusto de errores
    - Soporte para múltiples bancos mexicanos
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Inicializa el procesador OCR
        
        Args:
            openai_api_key: Clave API de OpenAI (opcional, usa variable de entorno si no se proporciona)
        """
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY es requerida")
        
        self.client = OpenAI(api_key=api_key)
        self.configuraciones_banco = self._cargar_configuraciones_banco()
    
    def procesar_estado_cuenta(self, pdf_bytes: bytes, empresa_id: int) -> Dict[str, Any]:
        """
        Procesa un estado de cuenta bancario completo
        
        Args:
            pdf_bytes: Contenido del PDF en bytes
            empresa_id: ID de la empresa
            
        Returns:
            Diccionario con datos extraídos y metadatos
            
        Raises:
            OCRError: Si hay errores en el procesamiento
        """
        inicio_tiempo = time.time()
        
        try:
            logger.info(f"Iniciando procesamiento OCR para empresa {empresa_id}")
            
            # 1. Validar PDF y calcular hash
            hash_archivo = calcular_hash_archivo(pdf_bytes)
            
            # 2. Convertir PDF a imágenes
            imagenes = self._convertir_pdf_a_imagenes(pdf_bytes)
            logger.info(f"PDF convertido a {len(imagenes)} imágenes")
            
            # 3. Detectar banco automáticamente
            banco_detectado = self._detectar_banco(imagenes[0])
            logger.info(f"Banco detectado: {banco_detectado}")
            
            # 4. Extraer metadatos del estado de cuenta
            metadatos = self._extraer_metadatos(imagenes[0], banco_detectado)
            
            # 5. Procesar cada página para extraer movimientos
            todos_movimientos = []
            errores_pagina = []
            
            # Extraer año del período para usar como referencia
            ano_referencia = None
            if metadatos.get("periodo_inicio"):
                try:
                    ano_referencia = datetime.fromisoformat(metadatos["periodo_inicio"]).year
                except Exception:
                    ano_referencia = datetime.now().year
            else:
                ano_referencia = datetime.now().year
            
            for i, imagen in enumerate(imagenes):
                try:
                    movimientos_pagina = self._procesar_pagina_movimientos(
                        imagen, banco_detectado, i + 1, ano_referencia
                    )
                    todos_movimientos.extend(movimientos_pagina)
                    logger.debug(f"Página {i+1}: {len(movimientos_pagina)} movimientos extraídos")
                except Exception as e:
                    error_msg = f"Error en página {i+1}: {str(e)}"
                    errores_pagina.append(error_msg)
                    logger.warning(error_msg)
            
            # 6. Validar y limpiar datos
            movimientos_limpios = self._validar_y_limpiar_movimientos(todos_movimientos, ano_referencia)
            
            # 7. Eliminar duplicados
            movimientos_unicos = self._eliminar_duplicados(movimientos_limpios)
            
            tiempo_total = time.time() - inicio_tiempo
            
            resultado = {
                "exito": True,
                "hash_archivo": hash_archivo,
                "banco_detectado": banco_detectado,
                "metadatos": metadatos,
                "movimientos": movimientos_unicos,
                "total_movimientos": len(movimientos_unicos),
                "paginas_procesadas": len(imagenes),
                "errores": errores_pagina,
                "tiempo_procesamiento": int(tiempo_total),
                "estadisticas": {
                    "movimientos_brutos": len(todos_movimientos),
                    "movimientos_despues_limpieza": len(movimientos_limpios),
                    "movimientos_despues_deduplicacion": len(movimientos_unicos),
                    "errores_pagina": len(errores_pagina)
                }
            }
            
            logger.info(f"OCR completado: {len(movimientos_unicos)} movimientos en {tiempo_total:.2f}s")
            return resultado
            
        except Exception as e:
            tiempo_total = time.time() - inicio_tiempo
            logger.error(f"Error en procesamiento OCR: {str(e)}")
            
            if isinstance(e, OCRError):
                raise
            else:
                raise OCRError(f"Error inesperado en OCR: {str(e)}")
    
    def _convertir_pdf_a_imagenes(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Convierte PDF a lista de imágenes usando PyMuPDF
        
        Args:
            pdf_bytes: Contenido del PDF
            
        Returns:
            Lista de imágenes PIL
            
        Raises:
            PDFProcessingError: Si hay errores en la conversión
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            imagenes = []
            
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    
                    # Configurar matriz para alta resolución
                    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom para mejor calidad
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convertir a PIL Image
                    img_data = pix.tobytes("png")
                    imagen = Image.open(io.BytesIO(img_data))
                    imagenes.append(imagen)
                    
                except Exception as e:
                    logger.warning(f"Error procesando página {page_num + 1}: {str(e)}")
                    continue
            
            doc.close()
            
            if not imagenes:
                raise PDFProcessingError("No se pudieron extraer páginas del PDF", "unknown")
            
            return imagenes
            
        except Exception as e:
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Error convirtiendo PDF: {str(e)}", "unknown", str(e))
    
    def _detectar_banco(self, imagen: Image.Image) -> TipoBanco:
        """
        Detecta automáticamente el banco del estado de cuenta
        
        Args:
            imagen: Primera página del estado de cuenta
            
        Returns:
            Tipo de banco detectado
            
        Raises:
            BancoNoReconocidoError: Si no se puede detectar el banco
        """
        try:
            # Convertir imagen a base64
            imagen_b64 = self._imagen_a_base64(imagen)
            
            prompt = """
            Analiza esta imagen de estado de cuenta bancario mexicano e identifica el banco.
            
            Busca logos, nombres, colores característicos y formato específico de estos bancos:
            - BBVA (antes Bancomer)
            - Santander
            - Banamex (Citibanamex)
            - Banorte
            - HSBC
            - Scotiabank
            - Inbursa
            - Azteca
            
            Responde ÚNICAMENTE con el nombre del banco en minúsculas, sin espacios ni caracteres especiales.
            Ejemplos de respuestas válidas: bbva, santander, banamex, banorte, hsbc, scotiabank, inbursa, azteca
            
            Si no puedes identificar el banco con certeza, responde: otro
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{imagen_b64}"}
                            }
                        ]
                    }
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            banco_detectado = response.choices[0].message.content.strip().lower()
            
            # Validar respuesta
            try:
                return TipoBanco(banco_detectado)
            except ValueError:
                # Si no es un banco válido, intentar mapear nombres alternativos
                mapeo_nombres = {
                    "bancomer": TipoBanco.BBVA,
                    "citibanamex": TipoBanco.BANAMEX,
                    "citibank": TipoBanco.BANAMEX,
                    "scotia": TipoBanco.SCOTIABANK,
                }
                
                if banco_detectado in mapeo_nombres:
                    return mapeo_nombres[banco_detectado]
                
                logger.warning(f"Banco no reconocido: {banco_detectado}")
                raise BancoNoReconocidoError(f"Banco detectado '{banco_detectado}' no está soportado")
        
        except Exception as e:
            if isinstance(e, BancoNoReconocidoError):
                raise
            
            logger.error(f"Error detectando banco: {str(e)}")
            raise handle_openai_error(e, "Detección de banco")
    
    def _extraer_metadatos(self, imagen: Image.Image, banco: TipoBanco) -> Dict[str, Any]:
        """
        Extrae metadatos del estado de cuenta (período, cuenta, saldos)
        
        Args:
            imagen: Primera página del estado de cuenta
            banco: Tipo de banco detectado
            
        Returns:
            Diccionario con metadatos extraídos
        """
        try:
            imagen_b64 = self._imagen_a_base64(imagen)
            
            config_banco = self.configuraciones_banco.get(banco.value, {})
            
            prompt = f"""
            Analiza esta primera página de estado de cuenta del banco {banco.value.upper()} y extrae los siguientes metadatos:

            1. PERÍODO DEL ESTADO DE CUENTA:
               - Fecha de inicio del período
               - Fecha de fin del período
               
            2. INFORMACIÓN DE LA CUENTA:
               - Número de cuenta (últimos 4 dígitos o cuenta completa si está visible)
               - Tipo de cuenta si es identificable
               
            3. SALDOS:
               - Saldo inicial del período
               - Saldo final del período
               
            4. INFORMACIÓN ADICIONAL:
               - Nombre del titular si está visible
               - Sucursal si está visible
               
            Busca esta información típicamente en el encabezado de la primera página.
            
            Responde en formato JSON con esta estructura exacta:
            {{
                "periodo_inicio": "YYYY-MM-DD",
                "periodo_fin": "YYYY-MM-DD", 
                "numero_cuenta": "string",
                "saldo_inicial": "decimal o null",
                "saldo_final": "decimal o null",
                "nombre_titular": "string o null",
                "sucursal": "string o null",
                "tipo_cuenta": "string o null"
            }}
            
            Si algún dato no es identificable, usa null.
            Para fechas usa formato YYYY-MM-DD.
            Para montos usa solo números decimales sin símbolos de moneda.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{imagen_b64}"}
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            resultado_json = response.choices[0].message.content.strip()
            
            # Limpiar respuesta si viene con markdown
            if resultado_json.startswith("```json"):
                resultado_json = resultado_json.replace("```json", "").replace("```", "").strip()
            
            metadatos = json.loads(resultado_json)
            
            # Validar y convertir tipos
            metadatos_procesados = self._procesar_metadatos(metadatos)
            
            logger.info(f"Metadatos extraídos para {banco.value}: {metadatos_procesados}")
            return metadatos_procesados
            
        except Exception as e:
            logger.warning(f"Error extrayendo metadatos: {str(e)}")
            # Retornar metadatos vacíos en caso de error
            return {
                "periodo_inicio": None,
                "periodo_fin": None,
                "numero_cuenta": None,
                "saldo_inicial": None,
                "saldo_final": None,
                "nombre_titular": None,
                "sucursal": None,
                "tipo_cuenta": None
            }
    
    def _procesar_pagina_movimientos(self, imagen: Image.Image, banco: TipoBanco, numero_pagina: int, ano_referencia: int = None) -> List[Dict[str, Any]]:
        """
        Procesa una página para extraer movimientos bancarios
        
        Args:
            imagen: Imagen de la página
            banco: Tipo de banco
            numero_pagina: Número de página
            
        Returns:
            Lista de movimientos extraídos
        """
        try:
            imagen_b64 = self._imagen_a_base64(imagen)
            
            prompt = f"""
            Analiza esta página {numero_pagina} de estado de cuenta del banco {banco.value.upper()} y extrae TODOS los movimientos bancarios.
            
            Para cada movimiento identifica:
            1. FECHA del movimiento (día/mes/año)
            2. CONCEPTO/DESCRIPCIÓN completa del movimiento
            3. MONTO (cantidad numérica)
            4. TIPO: "cargo" (débito/salida de dinero) o "abono" (crédito/entrada de dinero)
            5. REFERENCIA/FOLIO si está disponible
            6. SALDO después del movimiento (si está disponible)
            
            IMPORTANTE:
            - Busca en tablas, columnas o cualquier formato de listado
            - Los movimientos pueden estar en diferentes formatos según el banco
            - NO incluyas encabezados, totales o resúmenes
            - Solo movimientos individuales/transacciones específicas
            - Para el tipo, analiza el contexto del movimiento:
              * ABONO (entrada de dinero): depósitos, transferencias recibidas, "pago cuenta de tercero", "pago de tercero", ingresos, abonos
              * CARGO (salida de dinero): retiros, transferencias enviadas, "pago de servicio", "pago a tercero", comisiones, cargos
            - "PAGO CUENTA DE TERCERO" = ABONO (alguien te paga)
            - "PAGO DE SERVICIO" = CARGO (tú pagas algo)
            
            Responde en formato JSON como array de objetos:
            [
                {{
                    "fecha": "DD/MM/YYYY",
                    "concepto": "descripción completa del movimiento",
                    "monto": "cantidad decimal sin símbolos",
                    "tipo": "cargo o abono",
                    "referencia": "referencia/folio o null",
                    "saldo": "saldo resultante o null"
                }}
            ]
            
            Si no hay movimientos en esta página, responde: []
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url", 
                                "image_url": {"url": f"data:image/png;base64,{imagen_b64}"}
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            resultado_json = response.choices[0].message.content.strip()
            
            # Limpiar respuesta
            if resultado_json.startswith("```json"):
                resultado_json = resultado_json.replace("```json", "").replace("```", "").strip()
            
            movimientos = json.loads(resultado_json)
            
            # Validar que sea una lista
            if not isinstance(movimientos, list):
                logger.warning(f"Página {numero_pagina}: Respuesta no es una lista")
                return []
            
            # Agregar metadatos de página
            for mov in movimientos:
                mov["pagina_origen"] = numero_pagina
                mov["datos_ocr_raw"] = True
            
            logger.debug(f"Página {numero_pagina}: {len(movimientos)} movimientos extraídos")
            return movimientos
            
        except Exception as e:
            logger.error(f"Error procesando página {numero_pagina}: {str(e)}")
            return []
    
    def _validar_y_limpiar_movimientos(self, movimientos: List[Dict[str, Any]], ano_referencia: int = None) -> List[Dict[str, Any]]:
        """
        Valida y limpia los movimientos extraídos
        
        Args:
            movimientos: Lista de movimientos raw
            
        Returns:
            Lista de movimientos validados y limpios
        """
        movimientos_limpios = []
        
        for i, mov in enumerate(movimientos):
            try:
                # Validar campos requeridos
                if not mov.get("fecha") or not mov.get("concepto") or not mov.get("monto"):
                    logger.debug(f"Movimiento {i}: Campos requeridos faltantes")
                    continue
                
                # Limpiar y validar fecha
                fecha_limpia = self._limpiar_fecha(mov["fecha"], ano_referencia)
                if not fecha_limpia:
                    logger.debug(f"Movimiento {i}: Fecha inválida: {mov['fecha']}")
                    continue
                
                # Limpiar concepto
                concepto_limpio = normalizar_texto(mov["concepto"])
                if len(concepto_limpio) < 3:
                    logger.debug(f"Movimiento {i}: Concepto muy corto: {concepto_limpio}")
                    continue
                
                # Validar y limpiar monto
                monto_limpio = self._limpiar_monto(mov["monto"])
                if monto_limpio is None or monto_limpio <= 0:
                    logger.debug(f"Movimiento {i}: Monto inválido: {mov['monto']}")
                    continue
                
                # Validar tipo
                tipo_limpio = self._limpiar_tipo(mov.get("tipo", ""))
                if not tipo_limpio:
                    logger.debug(f"Movimiento {i}: Tipo inválido: {mov.get('tipo')}")
                    continue
                
                # Crear movimiento limpio
                movimiento_limpio = {
                    "fecha": fecha_limpia,
                    "concepto": concepto_limpio,
                    "monto": monto_limpio,
                    "tipo": tipo_limpio,
                    "referencia": self._limpiar_referencia(mov.get("referencia")),
                    "saldo": self._limpiar_monto(mov.get("saldo")),
                    "pagina_origen": mov.get("pagina_origen"),
                    "datos_ocr": {
                        "fecha_raw": mov["fecha"],
                        "concepto_raw": mov["concepto"],
                        "monto_raw": mov["monto"],
                        "tipo_raw": mov.get("tipo"),
                        "procesado_en": datetime.now().isoformat()
                    }
                }
                
                movimientos_limpios.append(movimiento_limpio)
                
            except Exception as e:
                logger.debug(f"Error limpiando movimiento {i}: {str(e)}")
                continue
        
        logger.info(f"Limpieza completada: {len(movimientos_limpios)}/{len(movimientos)} movimientos válidos")
        return movimientos_limpios
    
    def _eliminar_duplicados(self, movimientos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Elimina movimientos duplicados basándose en fecha, monto y concepto
        
        Args:
            movimientos: Lista de movimientos
            
        Returns:
            Lista sin duplicados
        """
        vistos = set()
        unicos = []
        
        for mov in movimientos:
            # Crear clave única para detectar duplicados
            clave = (
                mov["fecha"].strftime("%Y-%m-%d"),
                str(mov["monto"]),
                mov["concepto"][:100]  # Primeros 100 caracteres del concepto
            )
            
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(mov)
            else:
                logger.debug(f"Duplicado eliminado: {clave}")
        
        logger.info(f"Deduplicación: {len(unicos)}/{len(movimientos)} movimientos únicos")
        return unicos
    
    # === MÉTODOS AUXILIARES ===
    
    def _imagen_a_base64(self, imagen: Image.Image) -> str:
        """Convierte imagen PIL a base64"""
        buffer = io.BytesIO()
        imagen.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    
    def _limpiar_fecha(self, fecha_str: str, ano_referencia: int = None) -> Optional[datetime]:
        """Limpia y parsea fecha"""
        if not fecha_str:
            return None
        
        # Patrones de fecha comunes
        patrones_con_ano = [
            "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y",
            "%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"
        ]
        
        # Patrones sin año (para páginas siguientes)
        patrones_sin_ano = [
            "%d/%b", "%d/%B", "%d-%b", "%d-%B"  # 02/MAY, 02/MAYO, etc.
        ]
        
        fecha_limpia = fecha_str.strip().replace(" ", "").upper()
        
        # Intentar primero con patrones que incluyen año
        for patron in patrones_con_ano:
            try:
                fecha = datetime.strptime(fecha_limpia, patron)
                
                # Detectar si el año original era de 2 dígitos para aplicar lógica inteligente
                # strptime con %y convierte automáticamente: 00-68→2000-2068, 69-99→1969-1999
                es_ano_2_digitos = (patron.endswith('%y') or 
                                   (len(fecha_limpia.split('/')[-1]) == 2) or 
                                   (len(fecha_limpia.split('-')[-1]) == 2) or
                                   (len(fecha_limpia.split('.')[-1]) == 2))
                
                if es_ano_2_digitos and ano_referencia:
                    # Para años de 2 dígitos con año de referencia, usar lógica inteligente
                    ano_2_digitos_original = int(fecha_limpia.split('/')[-1]) if '/' in fecha_limpia else int(fecha_limpia.split('-')[-1])
                    ano_referencia_2_digitos = ano_referencia % 100  # 25 para 2025
                    
                    # Estrategia: Si el año de 2 dígitos está cerca del año de referencia (±5), 
                    # mapear directamente al año de referencia (muy común en estados de cuenta)
                    diferencia_2_digitos = abs(ano_2_digitos_original - ano_referencia_2_digitos)
                    
                    if diferencia_2_digitos <= 5:
                        # Casos comunes: 23/24/25/26/27 en período 2025 → todos son 2025
                        fecha = fecha.replace(year=ano_referencia)
                    else:
                        # Para diferencias mayores, usar interpretación estándar pero validar
                        ano_strptime = fecha.year
                        if abs(ano_strptime - ano_referencia) <= 2:
                            # Si strptime da un año muy cercano al de referencia, usar el de referencia
                            fecha = fecha.replace(year=ano_referencia)
                        elif abs(ano_strptime - ano_referencia) > 50:
                            # Si strptime da un año muy alejado, forzar al de referencia
                            fecha = fecha.replace(year=ano_referencia)
                        # Si no, mantener la interpretación de strptime
                
                return fecha
            except ValueError:
                continue
        
        # Si no funcionó y tenemos año de referencia, intentar patrones sin año
        if ano_referencia:
            for patron in patrones_sin_ano:
                try:
                    # Parsear solo día y mes
                    fecha_parcial = datetime.strptime(fecha_limpia, patron)
                    # Usar el año de referencia
                    fecha = fecha_parcial.replace(year=ano_referencia)
                    return fecha
                except ValueError:
                    continue
        
        return None
    
    def _limpiar_monto(self, monto_str: Any) -> Optional[Decimal]:
        """Limpia y convierte monto a Decimal"""
        if monto_str is None:
            return None
        
        try:
            # Convertir a string si no lo es
            monto_str = str(monto_str)
            
            # Remover símbolos de moneda y espacios
            monto_limpio = monto_str.replace("$", "").replace(",", "").replace(" ", "")
            
            # Manejar paréntesis (números negativos)
            if monto_limpio.startswith("(") and monto_limpio.endswith(")"):
                monto_limpio = "-" + monto_limpio[1:-1]
            
            return Decimal(monto_limpio)
            
        except (ValueError, TypeError):
            return None
    
    def _limpiar_tipo(self, tipo_str: str) -> Optional[TipoMovimiento]:
        """Limpia y valida tipo de movimiento"""
        if not tipo_str:
            return None
        
        tipo_lower = tipo_str.lower().strip()
        
        # Casos específicos que tienen prioridad sobre las reglas generales
        casos_especificos_abono = [
            "pago cuenta de tercero",
            "pago de tercero", 
            "transferencia recibida",
            "deposito de tercero",
            "abono por transferencia",
            "recepcion de transferencia"
        ]
        
        casos_especificos_cargo = [
            "pago de servicio",
            "pago a tercero",
            "transferencia enviada",
            "envio de transferencia"
        ]
        
        # Verificar casos específicos primero
        for caso in casos_especificos_abono:
            if caso in tipo_lower:
                return TipoMovimiento.ABONO
        
        for caso in casos_especificos_cargo:
            if caso in tipo_lower:
                return TipoMovimiento.CARGO
        
        # Mapeo de términos generales (sin "pago" que es ambiguo)
        mapeo_cargo = ["cargo", "debito", "débito", "retiro", "salida", "comision", "comisión"]
        mapeo_abono = ["abono", "credito", "crédito", "deposito", "depósito", "ingreso", "entrada"]
        
        if any(term in tipo_lower for term in mapeo_cargo):
            return TipoMovimiento.CARGO
        elif any(term in tipo_lower for term in mapeo_abono):
            return TipoMovimiento.ABONO
        
        return None
    
    def _limpiar_referencia(self, referencia_str: Any) -> Optional[str]:
        """Limpia referencia bancaria"""
        if not referencia_str or str(referencia_str).lower() in ["null", "none", ""]:
            return None
        
        return str(referencia_str).strip()[:255]  # Truncar a 255 caracteres
    
    def _procesar_metadatos(self, metadatos_raw: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa y valida metadatos extraídos"""
        resultado = {}
        
        # Procesar fechas
        for campo_fecha in ["periodo_inicio", "periodo_fin"]:
            fecha_str = metadatos_raw.get(campo_fecha)
            if fecha_str and fecha_str != "null":
                fecha_obj = self._limpiar_fecha(fecha_str)
                # Convertir datetime a string para JSON serialization
                resultado[campo_fecha] = fecha_obj.isoformat() if fecha_obj else None
            else:
                resultado[campo_fecha] = None
        
        # Procesar montos
        for campo_monto in ["saldo_inicial", "saldo_final"]:
            monto_str = metadatos_raw.get(campo_monto)
            if monto_str and monto_str != "null":
                monto_obj = self._limpiar_monto(monto_str)
                # Convertir Decimal a string para JSON serialization
                resultado[campo_monto] = str(monto_obj) if monto_obj is not None else None
            else:
                resultado[campo_monto] = None
        
        # Campos de texto
        for campo_texto in ["numero_cuenta", "nombre_titular", "sucursal", "tipo_cuenta"]:
            valor = metadatos_raw.get(campo_texto)
            if valor and valor != "null":
                resultado[campo_texto] = str(valor).strip()
            else:
                resultado[campo_texto] = None
        
        return resultado
    
    def _cargar_configuraciones_banco(self) -> Dict[str, Dict[str, Any]]:
        """Carga configuraciones específicas por banco"""
        return {
            TipoBanco.BBVA.value: {
                "formatos_fecha": ["%d/%m/%Y", "%d-%m-%Y"],
                "patrones_referencia": [r"REF\s*\d+", r"AUT\s*\d+"],
                "columnas_esperadas": ["fecha", "concepto", "cargo", "abono", "saldo"]
            },
            TipoBanco.SANTANDER.value: {
                "formatos_fecha": ["%d/%m/%Y", "%d-%m-%Y"],
                "patrones_referencia": [r"OP\s*\d+", r"MOV\s*\d+"],
                "columnas_esperadas": ["fecha", "descripcion", "importe", "saldo"]
            },
            TipoBanco.BANAMEX.value: {
                "formatos_fecha": ["%d/%m/%y", "%d/%m/%Y"],
                "patrones_referencia": [r"FOL\s*\d+", r"TRF\s*\d+"],
                "columnas_esperadas": ["fecha", "concepto", "monto", "tipo", "saldo"]
            }
        } 