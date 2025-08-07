import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from google import genai
from google.genai import types

from app.core.config import settings


logger = logging.getLogger(__name__)

class GeminiProcessor:
    #Procesador de PDFs usando Google Gemini API con selección automática de modelo
    
    def __init__(self):
        #Inicializa el procesador Gemini con configuración automática de modelo
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Error de configuración del procesador Gemini: GEMINI_API_KEY no encontrada")
        
        logger.info(f"🔑 Gemini API Key configurada: {self.api_key[:10]}...")
        
        # Configuración inicial del modelo
        self.model_id = "gemini-2.5-flash-lite"  # Modelo por defecto
        self.client = genai.Client(api_key=self.api_key)
        
        logger.info(f"🤖 Modelo Gemini inicial: {self.model_id}")
    
    def _obtener_numero_paginas(self, pdf_path: str) -> int:
        #Obtiene el número de páginas de un PDF
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            num_paginas = len(doc)
            doc.close()
            return num_paginas
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener número de páginas: {e}")
            return 1  # Valor por defecto
    
    def _detectar_banco_por_contenido_pdf(self, pdf_path: str) -> str:
        """Detecta el banco basándose en el contenido del PDF."""
        try:
            # Extraer texto del PDF
            texto_pdf = ""
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            for page in doc:
                texto_pdf += page.get_text() + " "
            doc.close()
            
            # Detectar banco por palabras clave en el texto
            texto_upper = texto_pdf.upper()
            
            # Detectar BBVA (prioridad máxima - más específico)
            bbva_keywords = [
                'BBVA', 'BANCO BBVA', 'CUENTA BBVA', 'BNET01002506200029230973',
                'BNET01002506200029231831', 'BNET 0142201275', 'BNET 0193305422',
                'BNET01002506200029231831', 'BNET01002506200029230973',
                'FECHA SALDO OPER LIQ COD. DESCRIPCIÓN REFERENCIA CARGOS ABONOS OPERACIÓN LIQUIDACIÓN',
                'OPER LIQ COD. DESCRIPCIÓN REFERENCIA CARGOS ABONOS OPERACIÓN LIQUIDACIÓN',
                'BNET01002506200029230973', 'BNET01002506200029231831',
                'SPEI ENVIADO BANREGIO', 'SPEI RECIBIDOBANORTE', 'SPEI RECIBIDOSANTANDER',
                'PAGO CUENTA DE TERCERO', 'BNET 0142201275', 'BNET 0193305422',
                'BBVA MEXICO, S.A., INSTITUCION DE BANCA MULTIPLE', 'BBVA MEXICO, S.A.',
                'ESTADO DE CUENTA BBVA', 'CUENTA BBVA PYME', 'BBVA MEXICO, S.A., INSTITUCION DE BANCA MULTIPLE, GRUPO FINANCIERO BBVA MEXICO',
                'MAESTRA PYME BBVA', 'BBVA MEXICO, S.A., INSTITUCION DE BANCA MULTIPLE, GRUPO FINANCIERO BBVA MEXICO',
                'OPER LIQ COD.', 'FECHA SALDO', 'OPERACIÓN LIQUIDACIÓN', 'MAESTRA PYME BBVA'
            ]
            for keyword in bbva_keywords:
                if keyword in texto_upper:
                    logger.info(f"🏦 Detectado BBVA por palabra clave: {keyword}")
                    return "BBVA"
            
            # Detectar SANTANDER (prioridad alta - más específico)
            santander_keywords = [
                'SANTANDER', 'CUENTA SANTANDER PYME', 'BANCO SANTANDER MEXICO',
                'DETALLE DE MOVIMIENTOS CUENTA DE CHEQUES', 'CUENTA DE CHEQUES',
                'CORPORACION INDUSTRIAL TEXDUO', 'BANCO SANTANDER MEXICO S.A.',
                'CUENTA SANTANDER PYME 65-50573448-2', 'BANCO SANTANDER MEXICO S.A., INSTITUCION DE BANCA MULTIPLE',
                'SALDO FINAL DEL PERIODO ANTERIOR', 'DEPOSITO EN EFECTIVO', 'CARGO PAGO NOMINA',
                'PAGO TRANSFERENCIA SPEI', 'COM MEMBRESIA CUENTA E PYME', 'BANCO SANTANDER MEXICO S.A., INSTITUCION DE BANCA MULTIPLE, GRUPO FINANCIERO SANTANDER MEXICO'
            ]
            for keyword in santander_keywords:
                if keyword in texto_upper:
                    logger.info(f"🏦 Detectado SANTANDER por palabra clave: {keyword}")
                    return "SANTANDER"
            
            # Detectar BANORTE (prioridad alta - más específico)
            banorte_keywords = [
                'BANORTE', 'CUENTA BANORTE', 'BANCO BANORTE', 'CUENTAS POR PAGAR - SAP',
                'TRASPASO A CUENTA DE TERCEROS', 'COMPRA ORDEN DE PAGO SPEI',
                'DEPOSITO DE CUENTA DE TERCEROS', 'SPEI RECIBIDO, BCO:',
                'MONTO DEL DEPOSITO MONTO DEL RETIRO SALDO', 'BANCO BANORTE S.A., INSTITUCION DE BANCA MULTIPLE',
                'ESTADO DE CUENTA BANORTE', 'CUENTA BANORTE PYME', 'BANCO BANORTE S.A.',
                'FECHA DESCRIPCIÓN / ESTABLECIMIENTO MONTO DEL DEPOSITO MONTO DEL RETIRO SALDO',
                'BANCO BANORTE S.A., INSTITUCION DE BANCA MULTIPLE, GRUPO FINANCIERO BANORTE'
            ]
            for keyword in banorte_keywords:
                if keyword in texto_upper:
                    logger.info(f"🏦 Detectado BANORTE por palabra clave: {keyword}")
                    return "BANORTE"
            
            # Detectar INBURSA (prioridad media - más específico)
            inbursa_keywords = [
                'INBURSA', 'BANCO INBURSA', 'CUENTA INBURSA', 'TASA DE DESCTO',
                'LIQUIDACION ADQUIRENTE', 'INTERESES GANADOS', 'BALANCE INICIAL',
                'LIQUIDACION ADQ CREDITO', 'LIQUIDACION ADQ DEBITO',
                'APLICACION DE TASAS DE DESCUENTO', 'DEPOSITO TEF',
                'OPERADORA PAYPAL DE MEXICO', 'CUENTA 50058959195',
                'BANCO INBURSA S.A., INSTITUCION DE BANCA MULTIPLE', 'BANCO INBURSA S.A.',
                'ESTADO DE CUENTA INBURSA', 'CUENTA INBURSA PYME', 'BANCO INBURSA S.A., INSTITUCION DE BANCA MULTIPLE, GRUPO FINANCIERO INBURSA',
                'INBURSA S.A., INSTITUCION DE BANCA MULTIPLE', 'INBURSA S.A.'
            ]
            for keyword in inbursa_keywords:
                if keyword in texto_upper:
                    logger.info(f"🏦 Detectado INBURSA por palabra clave: {keyword}")
                    return "INBURSA"
            
            return "No detectado"
            
        except Exception as e:
            logger.error(f"❌ Error en detección por contenido: {e}")
            return "No detectado"
    
    def _determinar_modelo_por_paginas(self, num_paginas: int) -> str:
        #Determina qué modelo usar basado en el número de páginas.
        if num_paginas <= 10:
            # Para documentos pequeños, usar flash-lite (más rápido y económico)
            return "gemini-2.5-flash-lite"
        else:
            # Para documentos medianos y grandes, usar flash con más tokens
            return "gemini-2.5-flash"
    
    def _extraer_texto_pdf(self, pdf_path: str) -> str:
        """Extrae todo el texto plano del PDF (todas las páginas)."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            partes: list[str] = []
            for page in doc:
                partes.append(page.get_text())
            doc.close()
            return "\n".join(partes)
        except Exception as e:
            logger.error(f"❌ Error extrayendo texto del PDF: {e}")
            return ""

    def _procesar_por_chunks(self, pdf_path: str, num_paginas: int, banco_detectado_previo: str = None, chunk_size: int = 3, use_model: str = 'gemini-2.5-pro') -> Dict[str, Any]:
        """Procesa el PDF por chunks de tamaño fijo, usando Gemini Pro por chunk."""
        inicio = time.time()
        self.model_id = use_model
        logger.info(f"📚 Iniciando procesamiento por chunks de {chunk_size} con {use_model}")
        chunks = []
        for i in range(0, num_paginas, chunk_size):
            end_page = min(i + chunk_size, num_paginas)
            chunks.append((i + 1, end_page))
        logger.info(f"📋 Dividido en {len(chunks)} chunks")

        temperature = 0.1
        max_output_tokens = 65536
        todos_movs: list[dict] = []
        periodo_detectado = None

        for idx, (start_page, end_page) in enumerate(chunks):
            try:
                logger.info(f"🔄 Chunk {idx+1}/{len(chunks)} páginas {start_page}-{end_page}")
                prompt = self._crear_prompt_extraccion(banco_detectado_previo)
                import fitz
                doc = fitz.open(pdf_path)
                partes = []
                for p in range(start_page - 1, end_page):
                    if p < len(doc):
                        partes.append(doc[p].get_text())
                doc.close()
                texto = "\n".join(partes)
                if not texto:
                    continue
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=[prompt, texto],
                    config={
                        'temperature': temperature,
                        'max_output_tokens': max_output_tokens,
                        'response_mime_type': 'application/json',
                        'top_k': 1,
                    }
                )
                if not response or not response.text:
                    continue
                res = self._procesar_respuesta_gemini(response.text.strip(), banco_detectado_previo)
                if res and res.get('movimientos'):
                    todos_movs.extend(res['movimientos'])
                    if not periodo_detectado:
                        periodo_detectado = res.get('periodo_detectado')
            except Exception as e:
                logger.warning(f"⚠️ Error en chunk {idx+1}: {e}")
                continue

        movimientos = self._consolidar_movimientos(todos_movs)
        tiempo = time.time() - inicio
        logger.info(f"✅ Chunks completados: {len(movimientos)} movimientos")
        return {
            'exito': True,
            'mensaje': f"PDF procesado por chunks: {len(movimientos)} movimientos",
            'banco_detectado': banco_detectado_previo or 'No detectado',
            'periodo_detectado': periodo_detectado,
            'total_movimientos_extraidos': len(movimientos),
            'movimientos': movimientos,
            'modelo_utilizado': self.model_id,
            'tiempo_procesamiento_segundos': tiempo,
            'errores': []
        }

    def _procesar_por_n_chunks(self, pdf_path: str, num_paginas: int, banco_detectado_previo: str = None, num_chunks: int = 3, use_model: str = 'gemini-2.5-pro') -> Dict[str, Any]:
        """Procesa el PDF en exactamente num_chunks (distribución equitativa), usando Gemini Pro."""
        inicio = time.time()
        self.model_id = use_model
        logger.info(f"📚 Iniciando procesamiento en {num_chunks} chunks con {use_model}")

        # Calcular rangos equitativos
        base = num_paginas // num_chunks
        resto = num_paginas % num_chunks
        chunks: list[tuple[int,int]] = []
        start = 1
        for i in range(num_chunks):
            size = base + (1 if i < resto else 0)
            if size <= 0:
                continue
            end = start + size - 1
            chunks.append((start, min(end, num_paginas)))
            start = end + 1

        logger.info(f"📋 Rangos de chunks: {chunks}")

        temperature = 0.1
        max_output_tokens = 65536
        todos_movs: list[dict] = []
        periodo_detectado = None

        for idx, (start_page, end_page) in enumerate(chunks):
            try:
                logger.info(f"🔄 Chunk {idx+1}/{len(chunks)} páginas {start_page}-{end_page}")
                prompt = self._crear_prompt_extraccion(banco_detectado_previo)
                import fitz
                doc = fitz.open(pdf_path)
                partes = []
                for p in range(start_page - 1, end_page):
                    if p < len(doc):
                        partes.append(doc[p].get_text())
                doc.close()
                texto = "\n".join(partes)
                if not texto:
                    logger.warning("⚠️ Chunk sin texto, saltando")
                    continue
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=[prompt, texto],
                    config={
                        'temperature': temperature,
                        'max_output_tokens': max_output_tokens,
                        'response_mime_type': 'application/json',
                        'top_k': 1,
                    }
                )
                if not response or not response.text:
                    logger.warning("⚠️ Sin respuesta del modelo en chunk")
                    continue
                res = self._procesar_respuesta_gemini(response.text.strip(), banco_detectado_previo)
                if res and res.get('movimientos'):
                    todos_movs.extend(res['movimientos'])
                    if not periodo_detectado:
                        periodo_detectado = res.get('periodo_detectado')
            except Exception as e:
                logger.warning(f"⚠️ Error en chunk {idx+1}: {e}")
                continue

        movimientos = self._consolidar_movimientos(todos_movs)
        tiempo = time.time() - inicio
        logger.info(f"✅ Procesamiento en {num_chunks} chunks completado: {len(movimientos)} movimientos")
        return {
            'exito': True,
            'mensaje': f"PDF procesado en {num_chunks} chunks: {len(movimientos)} movimientos",
            'banco_detectado': banco_detectado_previo or 'No detectado',
            'periodo_detectado': periodo_detectado,
            'total_movimientos_extraidos': len(movimientos),
            'movimientos': movimientos,
            'modelo_utilizado': self.model_id,
            'tiempo_procesamiento_segundos': tiempo,
            'errores': []
        }
    
    def procesar_pdf(self, pdf_path: str, forzar_gemini: bool = False) -> Dict[str, Any]:
        #Procesa un PDF usando Gemini y extrae movimientos bancarios."""
        inicio = time.time()
        
        try:
            # Obtener número de páginas y determinar modelo
            num_paginas = self._obtener_numero_paginas(pdf_path)
            self.model_id = self._determinar_modelo_por_paginas(num_paginas)
            
            logger.info(f"📄 PDF con {num_paginas} páginas → Usando modelo {self.model_id}")
            
            # Detectar banco por contenido del PDF
            banco_detectado_previo = self._detectar_banco_por_contenido_pdf(pdf_path)
            logger.info(f"🏦 Banco detectado por contenido: {banco_detectado_previo}")

            # Modo forzado: extraer TODO el texto y enviarlo a Gemini con el prompt específico
            if forzar_gemini:
                logger.info("🧲 Modo forzado Gemini: extrayendo texto completo y procesando con prompt del banco")
                # Si el usuario fuerza banco BBVA, usar prompt BBVA explícitamente
                prompt = self._crear_prompt_extraccion(banco_detectado_previo or 'BBVA')
                texto_completo = self._extraer_texto_pdf(pdf_path)
                if not texto_completo:
                    tiempo_procesamiento = time.time() - inicio
                    return self._crear_respuesta_error("No se pudo extraer texto del PDF", tiempo_procesamiento)

                # Configurar parámetros
                temperature = 0.1
                max_output_tokens = 12192 if "flash-lite" in self.model_id else 65536
                logger.info(f"⚙️ Config (forzado): temperature={temperature}, max_tokens={max_output_tokens}")

                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=[prompt, texto_completo],
                    config={
                        'temperature': temperature,
                        'max_output_tokens': max_output_tokens,
                        'response_mime_type': 'application/json',
                        'top_k': 1,
                    }
                )

                if not response or not response.text:
                    tiempo_procesamiento = time.time() - inicio
                    return self._crear_respuesta_error("No se recibió respuesta del modelo Gemini", tiempo_procesamiento)

                response_text = response.text.strip()
                logger.info(f"✅ Respuesta (forzado) recibida de Gemini: {len(response_text)} caracteres")

                resultado = self._procesar_respuesta_gemini(response_text, banco_detectado_previo)

                # Forzar banco detectado por contenido
                if banco_detectado_previo != 'No detectado' and resultado is not None:
                    resultado['banco_detectado'] = banco_detectado_previo
                    logger.info(f"🔒 Forzando banco final (forzado): {banco_detectado_previo}")

                # Calcular tiempo total y consolidar
                tiempo_procesamiento = time.time() - inicio
                movimientos_consolidados = self._consolidar_movimientos(resultado.get('movimientos', [])) if resultado else []
                return {
                    'exito': bool(resultado),
                    'mensaje': f"PDF procesado exitosamente: {len(movimientos_consolidados)} movimientos extraídos" if resultado else "Error procesando PDF",
                    'banco_detectado': resultado.get('banco_detectado', 'No detectado') if resultado else banco_detectado_previo,
                    'periodo_detectado': resultado.get('periodo_detectado') if resultado else None,
                    'total_movimientos_extraidos': len(movimientos_consolidados),
                    'movimientos': movimientos_consolidados,
                    'modelo_utilizado': self.model_id,
                    'tiempo_procesamiento_segundos': tiempo_procesamiento,
                    'errores': [] if resultado else ["Fallo en procesamiento forzado"]
                }

            # Si el documento es mediano/grande, procesar en exactamente 3 chunks con Gemini Pro
            if num_paginas >= 10:
                return self._procesar_por_n_chunks(pdf_path, num_paginas, banco_detectado_previo, num_chunks=3, use_model='gemini-2.5-pro')
            
            # Si no se tomó la ruta de chunks previa, continuar con flujo normal
            
            # Subir el archivo
            uploaded_file = self.client.files.upload(
                file=pdf_path,
                config={'display_name': os.path.basename(pdf_path)}
            )
            
            # Crear el prompt usando el banco detectado
            prompt = self._crear_prompt_extraccion(banco_detectado_previo)
            
            # Configurar parámetros según el modelo
            temperature = 0.1
            if "flash-lite" in self.model_id:
                max_output_tokens = 12192  # Menos tokens para flash-lite
            else:
                max_output_tokens = 65536  # Muchos más tokens para flash (documentos grandes)
            
            logger.info(f"⚙️ Configuración del modelo: temperature={temperature}, max_tokens={max_output_tokens}")
            
            # Generar contenido
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, uploaded_file],
                config={
                    'temperature': temperature,
                    'max_output_tokens': max_output_tokens
                }
            )
            
            # Verificar respuesta
            if not response or not response.text:
                tiempo_procesamiento = time.time() - inicio
                return self._crear_respuesta_error("No se recibió respuesta del modelo Gemini", tiempo_procesamiento)
            
            response_text = response.text.strip()
            logger.info(f"✅ Respuesta recibida de Gemini: {len(response_text)} caracteres")
            
            # Procesar la respuesta
            resultado = self._procesar_respuesta_gemini(response_text, banco_detectado_previo)
            
            # FORZAR el banco detectado por contenido como prioridad absoluta
            if banco_detectado_previo != 'No detectado':
                resultado['banco_detectado'] = banco_detectado_previo
                logger.info(f"🔒 Forzando banco final: {banco_detectado_previo} (detectado por contenido)")
            else:
                logger.warning("⚠️ No se pudo detectar el banco")
            
            # Calcular tiempo total
            tiempo_procesamiento = time.time() - inicio
            
            # Consolidar movimientos
            movimientos_consolidados = self._consolidar_movimientos(resultado.get('movimientos', []))
            
            return {
                'exito': True,
                'mensaje': f"PDF procesado exitosamente: {len(movimientos_consolidados)} movimientos extraídos",
                'banco_detectado': resultado.get('banco_detectado', 'No detectado'),
                'periodo_detectado': resultado.get('periodo_detectado'),
                'total_movimientos_extraidos': len(movimientos_consolidados),
                'movimientos': movimientos_consolidados,
                'modelo_utilizado': self.model_id,
                'tiempo_procesamiento_segundos': tiempo_procesamiento,
                'errores': []
            }
            
        except Exception as e:
            tiempo_procesamiento = time.time() - inicio
            logger.error(f"❌ Error procesando PDF: {str(e)}")
            return self._crear_respuesta_error(f"Error interno Gemini: {str(e)}", tiempo_procesamiento)
    

    
    def _crear_prompt_extraccion(self, banco_detectado: str = None) -> str:
        """Crea el prompt para extracción de movimientos bancarios."""
        
        try:
            from .prompts.inbursa_prompt import crear_prompt_inbursa_estructurado
            from .prompts.bbva_prompt import crear_prompt_bbva_estructurado
            from .prompts.banorte_prompt import crear_prompt_banorte_estructurado
            from .prompts.santander_prompt import crear_prompt_santander_estructurado
            
            # Usar prompt específico según el banco detectado
            if banco_detectado == "SANTANDER":
                logger.info("📝 Usando prompt específico para SANTANDER")
                return crear_prompt_santander_estructurado()
            elif banco_detectado == "INBURSA":
                logger.info("📝 Usando prompt específico para INBURSA")
                return crear_prompt_inbursa_estructurado()
            elif banco_detectado == "BBVA":
                logger.info("📝 Usando prompt específico para BBVA")
                return crear_prompt_bbva_estructurado()
            elif banco_detectado == "BANORTE":
                logger.info("📝 Usando prompt específico para BANORTE")
                return crear_prompt_banorte_estructurado()
            else:
                logger.info("📝 Usando prompt general")
                return self._crear_prompt_general()
                
        except ImportError as e:
            logger.warning(f"⚠️ Error importando prompts específicos: {e}")
            return self._crear_prompt_general()

    def _crear_prompt_general(self) -> str:
        """Crea el prompt general para todos los bancos."""
        
        prompt = """
        # INSTRUCCIONES PARA EXTRACCIÓN DE MOVIMIENTOS BANCARIOS

        Tu tarea es extraer TODOS los movimientos bancarios del documento PDF y devolverlos en formato JSON.

        ## FORMATO DE RESPUESTA REQUERIDO:
        Debes devolver SOLO un array JSON con los movimientos, sin texto adicional.

        ```json
        [
          {
            "FECHA": "DD-MMM-YYYY",
            "DESCRIPCION": "Descripción del movimiento",
            "MONTO_DEL_DEPOSITO": "monto_con_comas",
            "MONTO_DEL_RETIRO": "monto_con_comas", 
            "SALDO": "saldo_con_comas"
          }
        ]
        ```
        
        ## REGLAS ESPECÍFICAS POR BANCO:

        ### SANTANDER:
        - Suele empezar con "DETALLE DE MOVIMIENTOS CUENTA DE CHEQUES"
        - Formato: FECHA | FOLIO | DESCRIPCIÓN | DEPOSITOS | RETIRO | SALDO
        - FOLIO = Número de referencia (ej: "3407784114")
        - DEPOSITOS = ABONO (ingreso)
        - RETIRO = CARGO (egreso)
        - En cada movimiento debe haber o un depósito o un retiro

        - Si no hay depósito, usar null para DEPOSITOS
        - Si no hay retiro, usar null para RETIRO
        - Ejemplos de conceptos: "DEPOSITO EN EFECTIVO", "CARGO PAGO NOMINA", "PAGO TRANSFERENCIA SPEI"
        - Buscar específicamente: "CORPORACION INDUSTRIAL TEXDUO", "CUENTA SANTANDER PYME 65-50573448-2"
        - Detectar movimientos como: "31-DIC-2023 SALDO FINAL DEL PERIODO ANTERIOR", "04-ENE-2024 6975217 DEPOSITO EN EFECTIVO"
        
        ### BANORTE:
        - Formato: FECHA | DESCRIPCIÓN | MONTO DEL DEPOSITO | MONTO DEL RETIRO | SALDO
        - Usar campos exactos: "MONTO DEL DEPOSITO", "MONTO DEL RETIRO", "DESCRIPCIÓN"
        - MONTO DEL DEPOSITO = ABONO (ingreso)
        - MONTO DEL RETIRO = CARGO (egreso)
        
        ### BBVA:
        - Formato: OPER | FECHA | SALDO | COD. | DESCRIPCIÓN | REFERENCIA
        - LIQUIDACION = SALDO (no es cargo ni abono, es saldo)
        - Detectar movimientos reales, no liquidaciones
        
        ### INBURSA:
        - Formato: FECHA REFERENCIA CONCEPTO (puede ser múltiples líneas) MONTO SALDO
        - Ejemplo real:
          MAY. 26 3438154784 IVA TASA DE DESCTO CREDITO
          Tasa IVA 16.0 %
          1.23 62,087.21
        - Conceptos pueden tener 2-3 líneas
        - Montos están en la última línea del concepto
        - Extraer TODOS los movimientos, incluyendo los de múltiples líneas
        - Manejar conceptos como "LIQUIDACION ADQUIRENTE DEBITO" + "LIQUIDACION ADQ DEBITO-8993380"
        - Detectar correctamente: DEPOSITO TEF, INTERESES GANADOS, COMISION MANEJO DE CUENTA

        ## REGLAS GENERALES:
        - NO incluir líneas de resumen como "TOTAL", "SALDO INICIAL", "SALDO FINAL"
        - NO incluir líneas de "DEPOSITOS", "RETIROS", "COMISIONES COBRADAS"
        - Solo extraer movimientos reales con montos
        - Mantener el formato de fechas original (DD-MMM-YYYY)
        - Usar comas en los números (ej: "1,234.56")
        - Si un campo no tiene valor, usar null

        ## INSTRUCCIONES ESPECIALES PARA DOCUMENTOS GRANDES:
        - Si el documento tiene muchas páginas, extraer TODOS los movimientos sin omitir ninguno
        - No detenerse en los primeros movimientos, continuar hasta el final
        - Buscar movimientos en todas las páginas del documento
        - Para documentos de 80+ páginas, procesar completamente sin límites
        - Asegurar que se extraigan movimientos de todas las secciones del documento

        ## IMPORTANTE:
        - Devuelve SOLO el JSON, sin texto adicional
        - No incluyas explicaciones ni comentarios
        - Asegúrate de que el JSON sea válido
        - Usa los nombres de campos exactos especificados
        """
        
        return prompt
    
    def _parsear_respuesta_json(self, response_text: str, banco_detectado_previo: str = None) -> Optional[Dict[str, Any]]:
        """Parsea la respuesta JSON de Gemini con mejor manejo de errores."""
        try:
            # Limpiar el texto de respuesta
            cleaned_text = response_text.strip()
            
            # Remover markdown si está presente
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # Intentar parsear directamente
            try:
                resultado = json.loads(cleaned_text)
                
                # Manejar caso donde Gemini devuelve una lista directamente
                if isinstance(resultado, list):
                    logger.info(f"✅ JSON parseado exitosamente (lista): {len(resultado)} movimientos")
                    # Usar todos los movimientos sin filtrar
                    logger.info(f"🔍 Movimientos sin filtrar: {len(resultado)}")
                    # Mapear los campos de cada movimiento
                    movimientos_mapeados = [self._mapear_campos_movimiento(mov) for mov in resultado]
                    # Usar banco detectado previamente si está disponible
                    banco_detectado = banco_detectado_previo if banco_detectado_previo and banco_detectado_previo != 'No detectado' else 'No detectado'
                    logger.info(f"🏦 Usando banco detectado previamente: {banco_detectado}")
                    return {
                        'banco_detectado': banco_detectado,
                        'periodo_detectado': None,
                        'movimientos': movimientos_mapeados
                    }
                # Manejar caso donde Gemini devuelve un objeto con movimientos
                elif isinstance(resultado, dict) and resultado.get('movimientos'):
                    logger.info(f"✅ JSON parseado exitosamente (objeto): {len(resultado.get('movimientos', []))} movimientos")
                    # Mapear los campos de cada movimiento
                    movimientos_mapeados = [self._mapear_campos_movimiento(mov) for mov in resultado.get('movimientos', [])]
                    resultado['movimientos'] = movimientos_mapeados
                    # Usar banco detectado previamente si está disponible
                    if banco_detectado_previo and banco_detectado_previo != 'No detectado':
                        resultado['banco_detectado'] = banco_detectado_previo
                        logger.info(f"🏦 Usando banco detectado previamente: {banco_detectado_previo}")
                return resultado
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Error en parsing JSON directo: {e}")
                
                # Intentar reparar JSON común
                repaired_text = self._reparar_json(cleaned_text)
                if repaired_text:
                    try:
                        resultado = json.loads(repaired_text)
                        
                        # Aplicar la misma lógica para el JSON reparado
                        if isinstance(resultado, list):
                            logger.info(f"✅ JSON reparado y parseado (lista): {len(resultado)} movimientos")
                            # Usar todos los movimientos sin filtrar
                            logger.info(f"🔍 Movimientos sin filtrar: {len(resultado)}")
                            # Mapear los campos de cada movimiento
                            movimientos_mapeados = [self._mapear_campos_movimiento(mov) for mov in resultado]
                            # Usar banco detectado previamente si está disponible
                            banco_detectado = banco_detectado_previo if banco_detectado_previo and banco_detectado_previo != 'No detectado' else 'No detectado'
                            logger.info(f"🏦 Usando banco detectado previamente: {banco_detectado}")
                            return {
                                'banco_detectado': banco_detectado,
                                'periodo_detectado': None,
                                'movimientos': movimientos_mapeados
                            }
                        elif isinstance(resultado, dict) and resultado.get('movimientos'):
                            logger.info(f"✅ JSON reparado y parseado (objeto): {len(resultado.get('movimientos', []))} movimientos")
                            # Mapear los campos de cada movimiento
                            movimientos_mapeados = [self._mapear_campos_movimiento(mov) for mov in resultado.get('movimientos', [])]
                            resultado['movimientos'] = movimientos_mapeados
                            # Usar banco detectado previamente si está disponible
                            if banco_detectado_previo and banco_detectado_previo != 'No detectado':
                                resultado['banco_detectado'] = banco_detectado_previo
                                logger.info(f"🏦 Usando banco detectado previamente: {banco_detectado_previo}")
                        return resultado
                            
                    except json.JSONDecodeError as e2:
                        logger.error(f"❌ Error en JSON reparado: {e2}")
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error parseando JSON: {e}")
            logger.error(f"📄 Texto de respuesta: {response_text[:500]}...")
            return None
    
    def _detectar_banco(self, movimientos: List[Dict[str, Any]]) -> str:
        """Detecta el banco basándose en los campos y patrones de los movimientos."""
        try:
            if not movimientos:
                return "No detectado"
            
            # Contar campos específicos de cada banco
            campos_santander = 0
            campos_banorte = 0
            campos_bbva = 0
            campos_inbursa = 0
            
            for mov in movimientos:
                # Detectar Santander por campos específicos (con espacios)
                if any(campo in mov for campo in ['MONTO DEL DEPOSITO', 'MONTO DEL RETIRO', 'DESCRIPCIÓN']):
                    campos_santander += 1
                
                # Detectar Banorte por campos específicos (sin espacios) - pero solo si NO es Santander
                if any(campo in mov for campo in ['MONTO_DEL_DEPOSITO', 'MONTO_DEL_RETIRO', 'DESCRIPCION']):
                    # Verificar que no sea Santander (que también puede tener estos campos)
                    concepto = mov.get('DESCRIPCION', '').upper()
                    if not any(palabra in concepto for palabra in [
                        'SANTANDER', 'CUENTA SANTANDER', 'BANCO SANTANDER', 'CORPORACION INDUSTRIAL TEXDUO',
                        'SALDO FINAL DEL PERIODO ANTERIOR', 'DEPOSITO EN EFECTIVO', 'CARGO PAGO NOMINA',
                        'PAGO TRANSFERENCIA SPEI', 'COM MEMBRESIA CUENTA E PYME'
                    ]):
                        campos_banorte += 1
                
                # Detectar BBVA por campos específicos
                if any(campo in mov for campo in ['OPER', 'COD.', 'LIQUIDACION']):
                    campos_bbva += 1
                
                # Detectar INBURSA por campos específicos
                if any(campo in mov for campo in ['TASA DE DESCTO', 'LIQUIDACION ADQUIRENTE', 'INTERESES GANADOS']):
                    campos_inbursa += 1
            
            # Determinar banco por mayoría de campos
            total_movimientos = len(movimientos)
            
            # Priorizar SANTANDER si tiene campos con espacios (más específico)
            if campos_santander > 0:
                logger.info(f"🏦 Detectado SANTANDER por {campos_santander} campos con espacios")
                return "SANTANDER"
            elif campos_banorte > 0:
                logger.info(f"🏦 Detectado BANORTE por {campos_banorte} campos sin espacios")
                return "BANORTE"
            elif campos_bbva > 0:
                logger.info(f"🏦 Detectado BBVA por {campos_bbva} campos específicos")
                return "BBVA"
            elif campos_inbursa > 0:
                logger.info(f"🏦 Detectado INBURSA por {campos_inbursa} campos específicos")
                return "INBURSA"
            else:
                logger.info(f"🏦 No se pudo detectar banco por campos")
                return "No detectado"
                
        except Exception as e:
            logger.error(f"❌ Error detectando banco: {e}")
            return "No detectado"

    def _detectar_banco_por_texto(self, response_text: str) -> str:
        """Detecta el banco basándose en el texto de respuesta de Gemini."""
        try:
            response_upper = response_text.upper()
            
            # Detectar SANTANDER por palabras clave específicas
            if any(palabra in response_upper for palabra in [
                'SANTANDER', 'CUENTA SANTANDER PYME', 'BANCO SANTANDER MEXICO',
                'DETALLE DE MOVIMIENTOS CUENTA DE CHEQUES', 'DEPOSITO EN EFECTIVO',
                'CARGO PAGO NOMINA', 'PAGO TRANSFERENCIA SPEI', 'CUENTA DE CHEQUES',
                'CORPORACION INDUSTRIAL TEXDUO', 'BANCO SANTANDER MEXICO S.A.',
                'CUENTA SANTANDER PYME 65-50573448-2', 'SALDO FINAL DEL PERIODO ANTERIOR',
                'CARGO PAGO NOMINA POR APLICAR', 'PAGO TRANSFERENCIA SPEI HORA',
                'COM MEMBRESIA CUENTA E PYME MEMBRESIA'
            ]):
                return "SANTANDER"
            
            # Detectar BANORTE por palabras clave
            if any(palabra in response_upper for palabra in [
                'BANORTE', 'CUENTA BANORTE', 'BANCO BANORTE', 'SPEI RECIBIDO',
                'DEPOSITO DE CUENTA DE TERCEROS', 'TRASPASO A CUENTA DE TERCEROS',
                'COMPRA ORDEN DE PAGO SPEI', 'CUENTAS POR PAGAR - SAP'
            ]):
                return "BANORTE"
            
            # Detectar BBVA por palabras clave
            if any(palabra in response_upper for palabra in [
                'BBVA', 'BANCO BBVA', 'CUENTA BBVA', 'COM TRANSACCIONES BNTC',
                'IVA COM TRANSACCIONE BNTC', 'COM SERV BBVA NET CAS',
                'IVA COM SERVICIOS BNTC', 'DETALLE DE MOVIMIENTOS REALIZADOS'
            ]):
                return "BBVA"
            
            # Detectar INBURSA por palabras clave
            if any(palabra in response_upper for palabra in [
                'INBURSA', 'BANCO INBURSA', 'CUENTA INBURSA', 'TASA DE DESCTO',
                'LIQUIDACION ADQUIRENTE', 'INTERESES GANADOS', 'BALANCE INICIAL',
                'LIQUIDACION ADQ CREDITO', 'LIQUIDACION ADQ DEBITO',
                'APLICACION DE TASAS DE DESCUENTO', 'DEPOSITO TEF',
                'OPERADORA PAYPAL DE MEXICO'
            ]):
                return "INBURSA"
            
            return "No detectado"
            
        except Exception as e:
            logger.error(f"❌ Error detectando banco por texto: {e}")
            return "No detectado"

    def _filtrar_movimientos_validos(self, movimientos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtra movimientos válidos, eliminando líneas de resumen y totales."""
        try:
            movimientos_validos = []
            
            # Palabras clave que indican líneas de resumen (no movimientos reales)
            palabras_resumen = [
                'TOTAL', 'SALDO INICIAL', 'SALDO FINAL', 'DEPOSITOS', 'RETIROS',
                'COMISIONES COBRADAS', 'INTERESES BRUTOS', 'INTERESES NETOS',
                'COMISION MANEJO DE CUENTA', 'RESUMEN', 'SUBTOTAL'
            ]
            
            for mov in movimientos:
                # Obtener descripción/concepto
                descripcion = mov.get('DESCRIPCIÓN', mov.get('DESCRIPCION', mov.get('concepto', '')))
                
                # Verificar si es un movimiento válido
                if descripcion and not any(palabra in descripcion.upper() for palabra in palabras_resumen):
                    # Verificar que tenga al menos un monto (cargo o abono)
                    tiene_monto = False
                    for campo in ['MONTO DEL DEPOSITO', 'MONTO DEL RETIRO', 'MONTO_DEL_DEPOSITO', 'MONTO_DEL_RETIRO']:
                        if campo in mov and mov[campo] is not None and str(mov[campo]).strip() != '':
                            tiene_monto = True
                            break
                    
                    if tiene_monto:
                        movimientos_validos.append(mov)
                        logger.debug(f"✅ Movimiento válido: {descripcion}")
                    else:
                        logger.debug(f"❌ Movimiento sin monto: {descripcion}")
                else:
                    logger.debug(f"❌ Línea de resumen filtrada: {descripcion}")
            
            return movimientos_validos
            
        except Exception as e:
            logger.error(f"❌ Error filtrando movimientos: {e}")
            return movimientos

    def _mapear_campos_movimiento(self, movimiento: Dict[str, Any]) -> Dict[str, Any]:
        """Mapea los campos de Gemini al formato esperado por el sistema."""
        try:
            mapeado = {}
            
            # Mapear fecha
            if 'FECHA' in movimiento:
                mapeado['fecha'] = movimiento['FECHA']
            elif 'fecha' in movimiento:
                mapeado['fecha'] = movimiento['fecha']
            
            # Mapear concepto/descripción
            if 'DESCRIPCION' in movimiento:
                mapeado['concepto'] = movimiento['DESCRIPCION']
            elif 'DESCRIPCIÓN' in movimiento:
                mapeado['concepto'] = movimiento['DESCRIPCIÓN']
            elif 'concepto' in movimiento:
                mapeado['concepto'] = movimiento['concepto']
            elif 'descripcion' in movimiento:
                mapeado['concepto'] = movimiento['descripcion']
            
            # Mapear referencia
            if 'REFERENCIA' in movimiento:
                mapeado['referencia'] = movimiento['REFERENCIA']
            elif 'referencia' in movimiento:
                mapeado['referencia'] = movimiento['referencia']
            elif 'FOLIO - REFERENCIA' in movimiento:
                mapeado['referencia'] = movimiento['FOLIO - REFERENCIA']
            elif 'FOLIO' in movimiento:
                mapeado['referencia'] = movimiento['FOLIO']
            elif 'folio' in movimiento:
                mapeado['referencia'] = movimiento['folio']
            
            # Mapear saldo
            if 'SALDO' in movimiento:
                saldo_str = str(movimiento['SALDO']).replace(',', '')
                try:
                    mapeado['saldo'] = float(saldo_str)
                except (ValueError, TypeError):
                    mapeado['saldo'] = None
            elif 'saldo' in movimiento:
                saldo_str = str(movimiento['saldo']).replace(',', '')
                try:
                    mapeado['saldo'] = float(saldo_str)
                except (ValueError, TypeError):
                    mapeado['saldo'] = None
            
            # Mapear cargos y abonos
            cargos = None
            abonos = None
            
            # Procesar MONTO DEL DEPOSITO (abono) - con espacios
            if 'MONTO DEL DEPOSITO' in movimiento and movimiento['MONTO DEL DEPOSITO'] is not None:
                monto_str = str(movimiento['MONTO DEL DEPOSITO']).replace(',', '')
                try:
                    abonos = float(monto_str)
                except (ValueError, TypeError):
                    abonos = None
            
            # Procesar MONTO DEL RETIRO (cargo) - con espacios
            if 'MONTO DEL RETIRO' in movimiento and movimiento['MONTO DEL RETIRO'] is not None:
                monto_str = str(movimiento['MONTO DEL RETIRO']).replace(',', '')
                try:
                    cargos = float(monto_str)
                except (ValueError, TypeError):
                    cargos = None
            
            # Procesar MONTO_DEL_DEPOSITO (abono) - sin espacios
            if 'MONTO_DEL_DEPOSITO' in movimiento and movimiento['MONTO_DEL_DEPOSITO'] is not None:
                monto_str = str(movimiento['MONTO_DEL_DEPOSITO']).replace(',', '')
                try:
                    abonos = float(monto_str)
                except (ValueError, TypeError):
                    abonos = None
            
            # Procesar MONTO_DEL_RETIRO (cargo) - sin espacios
            if 'MONTO_DEL_RETIRO' in movimiento and movimiento['MONTO_DEL_RETIRO'] is not None:
                monto_str = str(movimiento['MONTO_DEL_RETIRO']).replace(',', '')
                try:
                    cargos = float(monto_str)
                except (ValueError, TypeError):
                    cargos = None
            
            # Procesar CARGOS y ABONOS específicos de INBURSA
            if 'CARGOS' in movimiento and movimiento['CARGOS'] is not None:
                monto_str = str(movimiento['CARGOS']).replace(',', '')
                try:
                    cargos = float(monto_str)
                except (ValueError, TypeError):
                    cargos = None
            
            if 'ABONOS' in movimiento and movimiento['ABONOS'] is not None:
                monto_str = str(movimiento['ABONOS']).replace(',', '')
                try:
                    abonos = float(monto_str)
                except (ValueError, TypeError):
                    abonos = None
            
            # Si no hay campos específicos, intentar con campos genéricos
            if cargos is None and abonos is None:
                if 'cargos' in movimiento and movimiento['cargos'] is not None:
                    try:
                        cargos = float(str(movimiento['cargos']).replace(',', ''))
                    except (ValueError, TypeError):
                        cargos = None
                
                if 'abonos' in movimiento and movimiento['abonos'] is not None:
                    try:
                        abonos = float(str(movimiento['abonos']).replace(',', ''))
                    except (ValueError, TypeError):
                        abonos = None
                
                if 'monto' in movimiento and movimiento['monto'] is not None:
                    try:
                        monto = float(str(movimiento['monto']).replace(',', ''))
                        # Determinar si es cargo o abono basándose en el concepto
                        concepto = mapeado.get('concepto', '').upper()
                        if any(palabra in concepto for palabra in ['CARGO', 'RETIRO', 'PAGO', 'DEBITO', 'COBRO', 'TASA DE DESCTO', 'IVA']):
                            cargos = monto
                        else:
                            abonos = monto
                    except (ValueError, TypeError):
                        pass
            
            mapeado['cargos'] = cargos
            mapeado['abonos'] = abonos
            
            # Log detallado para debug
            logger.info(f"🔄 Mapeado movimiento:")
            logger.info(f"   Original: {movimiento}")
            logger.info(f"   Mapeado: {mapeado}")
            logger.info(f"   Cargos: {cargos}, Abonos: {abonos}")
            
            return mapeado
            
        except Exception as e:
            logger.error(f"❌ Error mapeando campos: {e}")
            return movimiento  # Devolver original si falla el mapeo
    
    def _reparar_json(self, json_text: str) -> Optional[str]:
        """Intenta reparar JSON malformado común."""
        try:
            # Caso 1: Comas faltantes al final de arrays/objects
            lines = json_text.split('\n')
            repaired_lines = []
            
            for i, line in enumerate(lines):
                # Si la línea termina con un valor y la siguiente es una llave de cierre, agregar coma
                if (line.strip().endswith('"') or line.strip().endswith('}') or line.strip().endswith(']')) and \
                   i + 1 < len(lines) and \
                   (lines[i + 1].strip().startswith('"') or lines[i + 1].strip().startswith('}') or lines[i + 1].strip().startswith(']')):
                    line = line.rstrip() + ','
                
                repaired_lines.append(line)
            
            repaired_text = '\n'.join(repaired_lines)
            
            # Caso 2: Remover comas extra al final de arrays/objects
            repaired_text = re.sub(r',(\s*[}\]])', r'\1', repaired_text)
            
            # Caso 3: Asegurar que el JSON esté completo
            if not repaired_text.strip().endswith('}'):
                # Buscar el último objeto completo
                last_brace = repaired_text.rfind('}')
                if last_brace > 0:
                    repaired_text = repaired_text[:last_brace + 1]
            
            # Caso 4: Manejar strings no terminados de manera simple
            # Contar comillas y cerrar si es necesario
            quote_count = repaired_text.count('"')
            if quote_count % 2 == 1:  # String no cerrado
                repaired_text += '"'
            
            # Caso 5: Manejar arrays y objetos no terminados
            if repaired_text.count('[') > repaired_text.count(']'):
                missing_brackets = repaired_text.count('[') - repaired_text.count(']')
                repaired_text += ']' * missing_brackets
            
            if repaired_text.count('{') > repaired_text.count('}'):
                missing_braces = repaired_text.count('{') - repaired_text.count('}')
                repaired_text += '}' * missing_braces
            
            return repaired_text
            
        except Exception as e:
            logger.error(f"❌ Error reparando JSON: {e}")
            return None
    
    def _procesar_respuesta_gemini(self, response_text: str, banco_detectado_previo: str = None) -> dict:
        """Procesa la respuesta de Gemini de manera robusta"""
        try:
            # Intentar parsear como JSON
            resultado = self._parsear_respuesta_json(response_text, banco_detectado_previo)
            if resultado:
                # Si el resultado ya tiene movimientos, devolverlo
                if resultado.get('movimientos'):
                    return resultado
                # Si el resultado es una lista (ya convertida a formato estándar)
                elif isinstance(resultado, dict) and 'movimientos' in resultado:
                    return resultado
                # Si el resultado es un diccionario pero no tiene movimientos, intentar extraer
                elif isinstance(resultado, dict):
                    logger.warning("⚠️ Resultado JSON no tiene movimientos, intentando extracción básica")
                    resultado_basico = self._extraer_info_basica(response_text)
                    if resultado_basico.get('movimientos'):
                        logger.info(f"✅ Extracción básica exitosa: {len(resultado_basico.get('movimientos', []))} movimientos")
                        return resultado_basico
            
            # Si falla el parsing JSON, intentar extraer información básica
            logger.warning("⚠️ Falló parsing JSON, intentando extracción básica")
            resultado_basico = self._extraer_info_basica(response_text)
            
            if resultado_basico.get('movimientos'):
                logger.info(f"✅ Extracción básica exitosa: {len(resultado_basico.get('movimientos', []))} movimientos")
                # SIEMPRE usar banco detectado previamente si está disponible
                if banco_detectado_previo and banco_detectado_previo != 'No detectado':
                    resultado_basico['banco_detectado'] = banco_detectado_previo
                    logger.info(f"🏦 Forzando banco detectado previamente: {banco_detectado_previo}")
                elif not resultado_basico.get('banco_detectado'):
                    banco_detectado = self._detectar_banco_por_texto(response_text)
                    logger.info(f"🏦 Banco detectado por texto: {banco_detectado}")
                    resultado_basico['banco_detectado'] = banco_detectado
                return resultado_basico
            else:
                logger.error("❌ No se pudieron extraer movimientos ni por JSON ni por extracción básica")
                # SIEMPRE usar banco detectado previamente si está disponible
                banco_detectado = banco_detectado_previo if banco_detectado_previo and banco_detectado_previo != 'No detectado' else "No detectado"
                if banco_detectado == "No detectado":
                    banco_detectado = self._detectar_banco_por_texto(response_text)
                    logger.info(f"🏦 Banco detectado por texto (sin movimientos): {banco_detectado}")
                else:
                    logger.info(f"🏦 Forzando banco detectado previamente (sin movimientos): {banco_detectado}")
                return {
                    'banco_detectado': banco_detectado,
                    'periodo_detectado': None,
                    'movimientos': []
                }
            
        except Exception as e:
            logger.error(f"❌ Error procesando respuesta: {str(e)}")
            # SIEMPRE usar banco detectado previamente si está disponible
            banco_detectado = banco_detectado_previo if banco_detectado_previo and banco_detectado_previo != 'No detectado' else "No detectado"
            if banco_detectado == "No detectado":
                try:
                    banco_detectado = self._detectar_banco_por_texto(response_text)
                    logger.info(f"🏦 Banco detectado por texto (error): {banco_detectado}")
                except:
                    pass
            else:
                logger.info(f"🏦 Forzando banco detectado previamente (error): {banco_detectado}")
            return {
                'banco_detectado': banco_detectado,
                'periodo_detectado': None,
                'movimientos': []
            }

    # ===================== OPTIMIZACIÓN PARA BBVA GRANDES =====================
    def _extraer_lineas_tabla_bbva(self, pdf_path: str, start_page: int, end_page: int) -> str:
        """
        Extrae SOLO las líneas relevantes de la tabla BBVA para reducir tokens.
        Mantiene: líneas que empiezan con FECHA (DD/MMM), líneas con 'Ref.' y líneas que
        son montos puros. Ignora encabezados, legales y contenido irrelevante.
        """
        try:
            import re
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            fecha_pat = re.compile(r"^\s*\d{2}/[A-ZÁÉÍÓÚÑ]{3}\b")
            ref_pat = re.compile(r"\bRef\.[^\n]*", re.IGNORECASE)
            monto_pat = re.compile(r"^\s*[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?\s*$")

            keep_lines: list[str] = []
            for p in range(max(0, start_page - 1), min(end_page, len(doc))):
                page_text = doc[p].get_text()
                # Normalizar espacios y dividir por líneas
                for raw_line in page_text.splitlines():
                    line = " ".join(raw_line.strip().split())
                    if not line:
                        continue
                    # Filtrar encabezados muy comunes
                    upper_line = line.upper()
                    if upper_line.startswith("FECHA SALDO"):
                        continue
                    if "OPER LIQ COD." in upper_line and "CARGOS" in upper_line and "ABONOS" in upper_line:
                        continue
                    if upper_line.startswith("DETALLE DE MOVIMIENTOS"):
                        continue

                    # Criterios de conservación
                    if fecha_pat.match(line):
                        keep_lines.append(line)
                        continue
                    if ref_pat.search(line):
                        keep_lines.append(line)
                        continue
                    if monto_pat.match(line):
                        keep_lines.append(line)
                        continue
                    # Algunas descripciones útiles (bancos en COD.)
                    if any(bank in upper_line for bank in [
                        "SPEI RECIBIDO", "SPEI ENVIADO", "PAGO CUENTA DE TERCERO",
                        "DEPOSITO EFECTIVO", "DEPOSITO EN EFECTIVO", "PRACTIC",
                        "BANORTE", "HSBC", "BAJIO", "INBURSA", "SCOTIABANK", "AZTECA"
                    ]):
                        keep_lines.append(line)

            doc.close()

            # Recortar exceso por seguridad
            texto = "\n".join(keep_lines)
            if len(texto) > 200_000:
                texto = texto[:200_000]
            return texto
        except Exception as e:
            logger.warning(f"⚠️ _extraer_lineas_tabla_bbva falló: {e}")
            return ""
    
    def _extraer_info_basica(self, response_text: str) -> dict:
        """Extrae información básica cuando falla el parsing JSON"""
        try:
            # Buscar patrones básicos en el texto
            banco_detectado = "No detectado"
            movimientos = []
            
            # Buscar indicadores de banco
            bancos = ["BANORTE", "BBVA", "BANAMEX", "SANTANDER", "BANJIO", "INBURSA"]
            for banco in bancos:
                if banco in response_text.upper():
                    banco_detectado = banco
                    break
            
            # Buscar movimientos en formato JSON parcial
            import re
            
            # Patrón para encontrar objetos de movimiento (más flexible)
            movimiento_pattern = r'\{[^}]*"fecha"[^}]*"referencia"[^}]*"concepto"[^}]*"monto"[^}]*"tipo_movimiento"[^}]*"saldo"[^}]*\}'
            movimientos_json = re.findall(movimiento_pattern, response_text, re.DOTALL)
            
            for movimiento_str in movimientos_json:
                try:
                    # Intentar reparar y parsear cada movimiento
                    movimiento_reparado = self._reparar_json(movimiento_str)
                    if movimiento_reparado:
                        movimiento_obj = json.loads(movimiento_reparado)
                        movimientos.append(movimiento_obj)
                except:
                    continue
            
            # Si no se encontraron movimientos JSON, buscar en líneas de texto
            if not movimientos:
                lines = response_text.split('\n')
                for line in lines:
                    if any(keyword in line.upper() for keyword in ["FECHA", "MONTO", "SALDO", "DEPOSITO", "RETIRO", "CARGO", "ABONO", "LIQUIDACION", "TASA", "COMISION"]):
                        # Intentar extraer información básica de la línea
                        movimiento = self._extraer_movimiento_basico(line)
                        if movimiento:
                            movimientos.append(movimiento)
            
            # Si aún no hay movimientos, buscar patrones más específicos para INBURSA
            if not movimientos:
                # Patrón específico para INBURSA real: FECHA REFERENCIA CONCEPTO (múltiples líneas) MONTO SALDO
                inbursa_pattern = r'([A-Z]{3}\.\s*\d{2})\s+([A-Z0-9]+)\s+(.+?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
                matches = re.findall(inbursa_pattern, response_text, re.MULTILINE | re.DOTALL)
                
                for match in matches:
                    fecha, referencia, concepto, monto, saldo = match
                    try:
                        monto_float = float(monto.replace(',', ''))
                        saldo_float = float(saldo.replace(',', ''))
                        
                        # Determinar tipo de movimiento basado en el concepto
                        concepto_upper = concepto.upper()
                        if any(keyword in concepto_upper for keyword in ["DEPOSITO", "INTERESES GANADOS", "LIQUIDACION ADQUIRENTE CREDITO", "TASA DE DESCTO CREDITO"]):
                            tipo = "abono"
                        elif any(keyword in concepto_upper for keyword in ["COMISION", "IVA", "ISR", "TASA DE DESCTO DEBITO", "LIQUIDACION ADQUIRENTE DEBITO"]):
                            tipo = "cargo"
                        else:
                            tipo = "cargo_o_abono"
                        
                        movimientos.append({
                            'fecha': fecha,
                            'referencia': referencia,
                            'concepto': concepto.strip(),
                            'monto': monto_float,
                            'tipo_movimiento': tipo,
                            'saldo': saldo_float
                        })
                    except:
                        continue
            
            # Si aún no hay movimientos, buscar patrones más simples para INBURSA
            if not movimientos:
                # Patrón más simple: fecha + referencia + concepto + monto + saldo
                simple_inbursa_pattern = r'([A-Z]{3}\.\s*\d{2})\s+([A-Z0-9]+)\s+(.+?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
                matches = re.findall(simple_inbursa_pattern, response_text, re.MULTILINE | re.DOTALL)
                
                for match in matches:
                    fecha, referencia, concepto, monto, saldo = match
                    try:
                        monto_float = float(monto.replace(',', ''))
                        saldo_float = float(saldo.replace(',', ''))
                        
                        # Determinar tipo de movimiento
                        concepto_upper = concepto.upper()
                        if any(keyword in concepto_upper for keyword in ["DEPOSITO", "INTERESES", "CREDITO"]):
                            tipo = "abono"
                        elif any(keyword in concepto_upper for keyword in ["COMISION", "IVA", "ISR", "DEBITO"]):
                            tipo = "cargo"
                        else:
                            tipo = "cargo_o_abono"
                        
                        movimientos.append({
                            'fecha': fecha,
                            'referencia': referencia,
                            'concepto': concepto.strip(),
                            'monto': monto_float,
                            'tipo_movimiento': tipo,
                            'saldo': saldo_float
                        })
                    except:
                        continue
            
            logger.info(f"✅ Extracción básica exitosa: {len(movimientos)} movimientos")
            
            return {
                'banco_detectado': banco_detectado,
                'periodo_detectado': None,
                'movimientos': movimientos
            }
            
        except Exception as e:
            logger.error(f"❌ Error en extracción básica: {str(e)}")
            return {
                'banco_detectado': 'No detectado',
                'periodo_detectado': None,
                'movimientos': []
            }
    
    def _extraer_movimiento_basico(self, line: str) -> dict:
        """Extrae información básica de una línea de movimiento"""
        try:
            # Buscar patrones básicos de fecha y monto
            import re
            
            # Patrón de fecha para INBURSA (MAY. 05, MAY. 26, etc.)
            fecha_pattern = r'([A-Z]{3}\.\s*\d{2})'
            fecha_match = re.search(fecha_pattern, line)
            fecha = fecha_match.group(1) if fecha_match else None
            
            # Patrón de referencia (números largos)
            referencia_pattern = r'(\d{10,})'
            referencia_match = re.search(referencia_pattern, line)
            referencia = referencia_match.group(1) if referencia_match else None
            
            # Patrón de monto (más flexible)
            monto_pattern = r'[\$]?([\d,]+\.?\d*)'
            monto_matches = re.findall(monto_pattern, line)
            
            # Buscar indicadores de cargo/abono en el concepto
            concepto_lower = line.lower()
            tipo_movimiento = "cargo_o_abono"
            
            # Indicadores de cargo
            if any(keyword in concepto_lower for keyword in ["cargo", "debito", "retiro", "comision", "tasa", "iva", "isr"]):
                tipo_movimiento = "cargo"
            # Indicadores de abono
            elif any(keyword in concepto_lower for keyword in ["abono", "credito", "deposito", "ingreso", "intereses"]):
                tipo_movimiento = "abono"
            
            if fecha and monto_matches:
                return {
                    'fecha': fecha,
                    'referencia': referencia,
                    'concepto': line[:100],  # Primeros 100 caracteres como concepto
                    'monto': float(monto_matches[0].replace(',', '')),
                    'tipo_movimiento': tipo_movimiento
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo movimiento básico: {str(e)}")
            return None
    
    def _consolidar_movimientos(self, movimientos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Consolida y mejora los movimientos extraídos."""
        movimientos_mejorados = []
        
        for mov in movimientos:
            try:
                # Extraer datos básicos
                fecha = mov.get("fecha", "")
                referencia = mov.get("referencia", "")
                concepto = mov.get("concepto", "")
                
                # Preservar valores originales de cargos y abonos si ya existen
                cargos_original = mov.get("cargos")
                abonos_original = mov.get("abonos")
                
                # Procesar saldo
                saldo_raw = mov.get("saldo")
                try:
                    saldo = float(saldo_raw) if saldo_raw is not None else 0.0
                    saldo = abs(saldo)  # Convert to absolute value
                except (ValueError, TypeError):
                    saldo = 0.0
                
                # Usar valores originales si existen, sino calcular
                if cargos_original is not None or abonos_original is not None:
                    cargos = cargos_original
                    abonos = abonos_original
                    logger.info(f"🔄 Preservando valores originales: cargos={cargos}, abonos={abonos}")
                else:
                    # Solo calcular si no existen valores originales
                    monto_raw = mov.get("monto")
                    try:
                        monto = float(monto_raw) if monto_raw is not None else 0.0
                        monto = abs(monto)  # Convert to absolute value
                    except (ValueError, TypeError):
                        monto = 0.0
                
                # Determinar tipo de movimiento
                tipo_movimiento = mov.get("tipo_movimiento", "")
                if not tipo_movimiento:
                    tipo_movimiento = self._mejorar_deteccion_tipo_movimiento(concepto, "")
                
                # Asignar montos según tipo
                cargos = monto if tipo_movimiento == "cargo" else None
                abonos = monto if tipo_movimiento == "abono" else None
                
                # Crear movimiento mejorado
                movimiento_mejorado = {
                    "fecha": fecha,
                    "referencia": referencia,
                    "concepto": concepto,
                    "cargos": cargos,
                    "abonos": abonos,
                    "saldo": saldo
                }
                
                movimientos_mejorados.append(movimiento_mejorado)
                
            except Exception as e:
                logger.warning(f"⚠️ Error procesando movimiento: {e}")
                continue
        
        return movimientos_mejorados
    
    def _mejorar_deteccion_tipo_movimiento(self, concepto: str, tipo_actual: Optional[str] = None) -> str:
        """Mejora la detección del tipo de movimiento basado en el concepto."""
        concepto_lower = concepto.upper()
        
        # Si ya hay un tipo definido, usarlo
        if tipo_actual and tipo_actual in ['cargo', 'abono']:
            return tipo_actual
        
        # PRIORIDAD 1: Indicadores de columnas específicas
        # BANORTE: MONTO DEL DEPOSITO = ABONO, MONTO DEL RETIRO = CARGO
        if "MONTO DEL DEPOSITO" in concepto_lower or "DEPOSITO" in concepto_lower:
            return "abono"
        if "MONTO DEL RETIRO" in concepto_lower or "RETIRO" in concepto_lower:
            return "cargo"
        
        # BBVA: LIQUIDACION = SALDO (no es cargo ni abono)
        if "LIQUIDACION" in concepto_lower:
            return "saldo"
        
        # INBURSA: Indicadores de columnas CARGOS y ABONOS
        if "CARGOS" in concepto_lower:
            return "cargo"
        if "ABONOS" in concepto_lower:
            return "abono"
        
        # PRIORIDAD 2: Palabras clave especiales
        if any(keyword in concepto_lower for keyword in ["DEPOSITO", "PAGO", "INGRESO", "ABONO", "CREDITO"]):
            return "abono"
        if any(keyword in concepto_lower for keyword in ["RETIRO", "CARGO", "DEBITO", "COMISION", "TASA"]):
            return "cargo"
        
        # PRIORIDAD 3: Palabras clave generales
        if any(keyword in concepto_lower for keyword in ["SPEI RECIBIDO", "TRANSFERENCIA RECIBIDA", "DEP.EFECTIVO"]):
            return "abono"
        if any(keyword in concepto_lower for keyword in ["SPEI ENVIADO", "TRANSFERENCIA ENVIADA", "PAGO TARJETA"]):
            return "cargo"
        
        # Por defecto
        return "cargo_o_abono"
    
    def _crear_respuesta_error(self, mensaje: str, tiempo_procesamiento: float = 0.0) -> Dict[str, Any]:
        """Crea una respuesta de error estandarizada"""
        return {
            "exito": False,
            "mensaje": mensaje,
            "banco_detectado": "desconocido",
            "periodo_detectado": None,
            "total_movimientos_extraidos": 0,
            "movimientos": [],
            "modelo_utilizado": self.model_id,
            "tiempo_procesamiento_segundos": round(tiempo_procesamiento, 2),
            "errores": [mensaje]
        } 

    def _procesar_pdf_grande(self, pdf_path: str, num_paginas: int, banco_detectado_previo: str = None) -> Dict[str, Any]:
        """Procesa PDFs grandes (80+ páginas) por chunks para mejor extracción."""
        inicio = time.time()
        logger.info(f"📚 Iniciando procesamiento por chunks para documento de {num_paginas} páginas")
        
        try:
            # Usar flash con más tokens para documentos grandes
            self.model_id = "gemini-2.5-flash"
            logger.info(f"🤖 Usando modelo flash: {self.model_id}")
            
            # Dividir el documento en chunks muy pequeños para evitar límites de tokens
            chunk_size = 5  # Chunks muy pequeños
            chunks = []
            for i in range(0, num_paginas, chunk_size):
                end_page = min(i + chunk_size, num_paginas)
                chunks.append((i + 1, end_page))
            
            logger.info(f"📋 Dividiendo en {len(chunks)} chunks de ~{chunk_size} páginas cada uno")
            
            # Procesar cada chunk
            todos_movimientos = []
            banco_detectado = banco_detectado_previo  # Usar el banco detectado previamente
            periodo_detectado = None
            
            if banco_detectado and banco_detectado != 'No detectado':
                logger.info(f"🏦 Banco fijo para todos los chunks: {banco_detectado}")
            
            # Preparar subida única como fallback (se usará solo si falla extracción de texto)
            uploaded_file_single = None
            
            for i, (start_page, end_page) in enumerate(chunks):
                logger.info(f"🔄 Procesando chunk {i+1}/{len(chunks)} (páginas {start_page}-{end_page})")
                
                # Crear prompt específico para chunks usando el banco detectado
                prompt_chunk = self._crear_prompt_extraccion(banco_detectado)
                prompt_chunk += f"\n\nIMPORTANTE: Estás procesando las páginas {start_page} a {end_page} de un documento de {num_paginas} páginas. Extrae TODOS los movimientos de estas páginas específicas."
                
                # Extraer texto optimizado (BBVA) para reducir tokens, o texto plano por fallback
                texto_chunk = None
                try:
                    if (banco_detectado or '').upper() == 'BBVA' and num_paginas >= 40:
                        texto_chunk = self._extraer_lineas_tabla_bbva(pdf_path, start_page, end_page)
                        if not texto_chunk:
                            raise ValueError('BBVA optimized extraction returned empty')
                    else:
                        import fitz  # PyMuPDF
                        doc = fitz.open(pdf_path)
                        partes = []
                        for p in range(start_page - 1, end_page):
                            if p < len(doc):
                                partes.append(doc[p].get_text())
                        doc.close()
                        texto_chunk = "\n".join(partes)
                        if texto_chunk and len(texto_chunk) > 200_000:
                            texto_chunk = texto_chunk[:200_000]
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo extraer texto para chunk {i+1}: {e}")
                    texto_chunk = None

                # Si no hay texto (fallback), preparar una sola subida reutilizable
                if texto_chunk is None:
                    if uploaded_file_single is None:
                        try:
                            uploaded_file_single = self.client.files.upload(
                    file=pdf_path,
                    config={'display_name': os.path.basename(pdf_path)}
                )
                        except Exception as e:
                            logger.error(f"❌ Error subiendo archivo para fallback en chunk {i+1}: {e}")
                            uploaded_file_single = None                
            # Consolidar todos los movimientos
            movimientos_consolidados = self._consolidar_movimientos(todos_movimientos)
            tiempo_procesamiento = time.time() - inicio
            
            # FORZAR el banco detectado previamente en el resultado final
            banco_final = banco_detectado_previo if banco_detectado_previo and banco_detectado_previo != 'No detectado' else banco_detectado
            if banco_final and banco_final != 'No detectado':
                logger.info(f"🔒 Forzando banco final: {banco_final}")
            
            logger.info(f"✅ Procesamiento por chunks completado: {len(movimientos_consolidados)} movimientos totales")
            logger.info(f"📊 Resumen: {len(chunks)} chunks procesados, {len(todos_movimientos)} movimientos extraídos")
            
            return {
                'exito': True,
                'mensaje': f"PDF grande procesado por chunks: {len(movimientos_consolidados)} movimientos extraídos",
                'banco_detectado': banco_final or 'No detectado',
                'periodo_detectado': periodo_detectado,
                'total_movimientos_extraidos': len(movimientos_consolidados),
                'movimientos': movimientos_consolidados,
                'modelo_utilizado': f"{self.model_id} (flash chunks)",
                'tiempo_procesamiento_segundos': tiempo_procesamiento,
                'errores': []
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando PDF grande: {e}")
            return self._crear_respuesta_error(f"Error procesando PDF grande: {e}", time.time() - inicio) 