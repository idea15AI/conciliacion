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

# Importar prompts específicos
try:
    from .prompts.inbursa_prompt import crear_prompt_inbursa_estructurado
except ImportError:
    # Fallback si no se puede importar
    def crear_prompt_inbursa_estructurado():
        return "Prompt INBURSA no disponible"

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
    
    def _determinar_modelo_por_paginas(self, num_paginas: int) -> str:
        #Determina qué modelo usar basado en el número de páginas.
        if num_paginas <= 5:
            # Para documentos pequeños, usar flash-lite (más rápido y económico)
            return "gemini-2.5-flash-lite"
        elif num_paginas <= 20:
            # Para documentos medianos, usar flash (balance entre velocidad y capacidad)
            return "gemini-2.5-flash"
        else:
            # Para documentos grandes, usar pro (máxima capacidad)
            return "gemini-2.5-pro"
    
    def procesar_pdf(self, pdf_path: str) -> Dict[str, Any]:
        #Procesa un PDF usando Gemini y extrae movimientos bancarios."""
        inicio = time.time()
        
        try:
            # Obtener número de páginas y determinar modelo
            num_paginas = self._obtener_numero_paginas(pdf_path)
            self.model_id = self._determinar_modelo_por_paginas(num_paginas)
            
            logger.info(f"📄 PDF con {num_paginas} páginas → Usando modelo {self.model_id}")
            
            # Para documentos muy grandes, usar procesamiento por chunks
            if num_paginas >= 40:
                logger.info(f"📚 Documento grande detectado ({num_paginas} páginas) → Procesamiento por chunks")
                return self._procesar_pdf_grande(pdf_path, num_paginas)
            
            # Subir el archivo
            uploaded_file = self.client.files.upload(
                file=pdf_path,
                config={'display_name': os.path.basename(pdf_path)}
            )
            
            # Crear el prompt
            prompt = self._crear_prompt_extraccion()
            
            # Configurar parámetros según el modelo
            temperature = 0.1
            if "flash-lite" in self.model_id:
                max_output_tokens = 8192  # Menos tokens para flash-lite
            elif "flash" in self.model_id:
                max_output_tokens = 16384  # Tokens intermedios para flash
            else:
                max_output_tokens = 65536  # Más tokens para modelo pro
            
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
                return self._crear_respuesta_error("No se recibió respuesta del modelo Gemini", tiempo_procesamiento)
            
            response_text = response.text.strip()
            logger.info(f"✅ Respuesta recibida de Gemini: {len(response_text)} caracteres")
            
            # Procesar la respuesta
            resultado = self._procesar_respuesta_gemini(response_text)
            
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
    
    def _crear_prompt_extraccion(self) -> str:
        """Crea el prompt para extracción de movimientos bancarios."""
        
        # Detectar si es INBURSA basado en el contexto
        # Por ahora usamos el prompt general, pero se puede mejorar la detección
        prompt = crear_prompt_inbursa_estructurado()
        
        # Reglas específicas por banco
        prompt += """
        
        ## REGLAS ESPECÍFICAS POR BANCO:
        
        ### BANORTE:
        - Formato: FECHA | DESCRIPCIÓN / ESTABLECIMIENTO | MONTO DEL DEPOSITO | MONTO DEL RETIRO | SALDO
        - MONTO DEL DEPOSITO = ABONO (ingreso)
        - MONTO DEL RETIRO = CARGO (egreso)
        - PRIORIDAD ABSOLUTA: Usar SOLO las columnas, sin usar el contexto del concepto
        - Todos los movimientos tienen tienen ya sea un cargo o un abono pero no ambos excepto el saldo inicial
        - Todos los movimientos tienen un saldo 
        - Verificar que cada movimiento tenga un cargo o un abono y un saldo
        - Ejemplos de ABONOS: "CUENTAS POR PAGAR - SAP", "DEPOSITOS", "PAGOS"
        - Ejemplos de CARGOS: "DISPOSICIONES", "RETIROS", "COMISIONES"
        
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


        ## INSTRUCCIONES ESPECIALES PARA DOCUMENTOS GRANDES:
        - Si el documento tiene muchas páginas, extraer TODOS los movimientos sin omitir ninguno
        - No detenerse en los primeros movimientos, continuar hasta el final
        - Buscar movimientos en todas las páginas del documento
        - Para documentos de 80+ páginas, procesar completamente sin límites
        - Asegurar que se extraigan movimientos de todas las secciones del documento
        """
        
        return prompt
    
    def _parsear_respuesta_json(self, response_text: str) -> Optional[Dict[str, Any]]:
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
                logger.info(f"✅ JSON parseado exitosamente: {len(resultado.get('movimientos', []))} movimientos")
                return resultado
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Error en parsing JSON directo: {e}")
                
                # Intentar reparar JSON común
                repaired_text = self._reparar_json(cleaned_text)
                if repaired_text:
                    try:
                        resultado = json.loads(repaired_text)
                        logger.info(f"✅ JSON reparado y parseado: {len(resultado.get('movimientos', []))} movimientos")
                        return resultado
                    except json.JSONDecodeError as e2:
                        logger.error(f"❌ Error en JSON reparado: {e2}")
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error parseando JSON: {e}")
            logger.error(f"📄 Texto de respuesta: {response_text[:500]}...")
            return None
    
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
    
    def _procesar_respuesta_gemini(self, response_text: str) -> dict:
        """Procesa la respuesta de Gemini de manera robusta"""
        try:
            # Intentar parsear como JSON
            resultado = self._parsear_respuesta_json(response_text)
            if resultado and resultado.get('movimientos'):
                return resultado
            
            # Si falla el parsing JSON, intentar extraer información básica
            logger.warning("⚠️ Falló parsing JSON, intentando extracción básica")
            resultado_basico = self._extraer_info_basica(response_text)
            
            if resultado_basico.get('movimientos'):
                logger.info(f"✅ Extracción básica exitosa: {len(resultado_basico.get('movimientos', []))} movimientos")
                return resultado_basico
            else:
                logger.error("❌ No se pudieron extraer movimientos ni por JSON ni por extracción básica")
                return {
                    'banco_detectado': 'No detectado',
                    'periodo_detectado': None,
                    'movimientos': []
                }
            
        except Exception as e:
            logger.error(f"❌ Error procesando respuesta: {str(e)}")
            return {
                'banco_detectado': 'No detectado',
                'periodo_detectado': None,
                'movimientos': []
            }
    
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
                
                # Procesar montos
                monto_raw = mov.get("monto")
                try:
                    monto = float(monto_raw) if monto_raw is not None else 0.0
                    monto = abs(monto)  # Convert to absolute value
                except (ValueError, TypeError):
                    monto = 0.0
                
                # Procesar saldo
                saldo_raw = mov.get("saldo")
                try:
                    saldo = float(saldo_raw) if saldo_raw is not None else 0.0
                    saldo = abs(saldo)  # Convert to absolute value
                except (ValueError, TypeError):
                    saldo = 0.0
                
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

    def _procesar_pdf_grande(self, pdf_path: str, num_paginas: int) -> Dict[str, Any]:
        """Procesa PDFs grandes (80+ páginas) por chunks para mejor extracción."""
        inicio = time.time()
        logger.info(f"📚 Iniciando procesamiento por chunks para documento de {num_paginas} páginas")
        
        try:
            # Usar el modelo más potente para documentos grandes
            self.model_id = "gemini-2.5-pro"
            logger.info(f"🤖 Usando modelo potente: {self.model_id}")
            
            # Dividir el documento en chunks de 20 páginas
            chunk_size = 20
            chunks = []
            for i in range(0, num_paginas, chunk_size):
                end_page = min(i + chunk_size, num_paginas)
                chunks.append((i + 1, end_page))
            
            logger.info(f"📋 Dividiendo en {len(chunks)} chunks de ~{chunk_size} páginas cada uno")
            
            # Procesar cada chunk
            todos_movimientos = []
            banco_detectado = None
            periodo_detectado = None
            
            for i, (start_page, end_page) in enumerate(chunks):
                logger.info(f"🔄 Procesando chunk {i+1}/{len(chunks)} (páginas {start_page}-{end_page})")
                
                # Crear prompt específico para chunks
                prompt_chunk = self._crear_prompt_extraccion()
                prompt_chunk += f"\n\nIMPORTANTE: Estás procesando las páginas {start_page} a {end_page} de un documento de {num_paginas} páginas. Extrae TODOS los movimientos de estas páginas específicas."
                
                # Subir archivo
                uploaded_file = self.client.files.upload(
                    file=pdf_path,
                    config={'display_name': os.path.basename(pdf_path)}
                )
                
                # Configurar parámetros según el modelo
                if "pro" in self.model_id:
                    temperature = 0.1
                    max_output_tokens = 65536
                else:
                    temperature = 0.1
                    max_output_tokens = 32768
                
                # Procesar chunk
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=[prompt_chunk, uploaded_file],
                    config={
                        'temperature': temperature,
                        'max_output_tokens': max_output_tokens
                    }
                )
                
                if response and response.text:
                    response_text = response.text.strip()
                    logger.info(f"✅ Chunk {i+1} procesado: {len(response_text)} caracteres")
                    
                    # Procesar respuesta del chunk
                    resultado_chunk = self._procesar_respuesta_gemini(response_text)
                    
                    # Acumular movimientos
                    if resultado_chunk.get('movimientos'):
                        todos_movimientos.extend(resultado_chunk.get('movimientos'))
                        logger.info(f"📊 Chunk {i+1}: {len(resultado_chunk.get('movimientos'))} movimientos extraídos")
                    
                    # Detectar banco y periodo del primer chunk
                    if i == 0:
                        banco_detectado = resultado_chunk.get('banco_detectado')
                        periodo_detectado = resultado_chunk.get('periodo_detectado')
                
                else:
                    logger.warning(f"⚠️ Chunk {i+1}: Sin respuesta válida")
            
            # Consolidar todos los movimientos
            movimientos_consolidados = self._consolidar_movimientos(todos_movimientos)
            tiempo_procesamiento = time.time() - inicio
            
            logger.info(f"✅ Procesamiento por chunks completado: {len(movimientos_consolidados)} movimientos totales")
            
            return {
                'exito': True,
                'mensaje': f"PDF grande procesado por chunks: {len(movimientos_consolidados)} movimientos extraídos",
                'banco_detectado': banco_detectado or 'No detectado',
                'periodo_detectado': periodo_detectado,
                'total_movimientos_extraidos': len(movimientos_consolidados),
                'movimientos': movimientos_consolidados,
                'modelo_utilizado': f"{self.model_id} (chunks)",
                'tiempo_procesamiento_segundos': tiempo_procesamiento,
                'errores': []
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando PDF grande: {e}")
            return self._crear_respuesta_error(f"Error procesando PDF grande: {e}", time.time() - inicio) 