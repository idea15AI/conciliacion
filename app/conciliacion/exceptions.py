"""
Excepciones personalizadas para el módulo de conciliación bancaria avanzada

Define una jerarquía de excepciones específicas para manejo de errores
"""

from typing import Optional, Dict, Any


class ConciliacionError(Exception):
    """Excepción base para errores de conciliación"""
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para APIs"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details
        }


class OCRError(ConciliacionError):
    """Errores relacionados con el procesamiento OCR"""
    
    def __init__(
        self, 
        message: str, 
        pdf_file: Optional[str] = None,
        page_number: Optional[int] = None,
        openai_error: Optional[str] = None
    ):
        details = {}
        if pdf_file:
            details["pdf_file"] = pdf_file
        if page_number:
            details["page_number"] = page_number
        if openai_error:
            details["openai_error"] = openai_error
            
        super().__init__(message, "OCR_ERROR", details)


class PDFProcessingError(OCRError):
    """Error específico de procesamiento de PDF"""
    
    def __init__(self, message: str, pdf_file: str, original_error: Optional[str] = None):
        details = {"pdf_file": pdf_file}
        if original_error:
            details["original_error"] = original_error
        super().__init__(message, pdf_file, details=details)


class BancoNoReconocidoError(OCRError):
    """Error cuando no se puede identificar el banco del estado de cuenta"""
    
    def __init__(self, message: str = "No se pudo identificar el banco del estado de cuenta"):
        super().__init__(message, code="BANCO_NO_RECONOCIDO")


class FormatoBancarioInvalidoError(OCRError):
    """Error cuando el formato del estado de cuenta no es válido"""
    
    def __init__(
        self, 
        message: str, 
        banco: Optional[str] = None,
        formato_esperado: Optional[str] = None
    ):
        details = {}
        if banco:
            details["banco"] = banco
        if formato_esperado:
            details["formato_esperado"] = formato_esperado
        super().__init__(message, code="FORMATO_INVALIDO", details=details)


class EmpresaNoEncontradaError(ConciliacionError):
    """Error cuando no se encuentra la empresa especificada"""
    
    def __init__(self, rfc: str):
        message = f"No se encontró empresa con RFC: {rfc}"
        super().__init__(message, "EMPRESA_NOT_FOUND", {"rfc": rfc})


class MovimientoNoEncontradoError(ConciliacionError):
    """Error cuando no se encuentra un movimiento bancario"""
    
    def __init__(self, movimiento_id: int):
        message = f"No se encontró movimiento bancario con ID: {movimiento_id}"
        super().__init__(message, "MOVIMIENTO_NOT_FOUND", {"movimiento_id": movimiento_id})


class CFDINoEncontradoError(ConciliacionError):
    """Error cuando no se encuentra un CFDI"""
    
    def __init__(self, uuid: str):
        message = f"No se encontró CFDI con UUID: {uuid}"
        super().__init__(message, "CFDI_NOT_FOUND", {"uuid": uuid})


class ConciliacionYaExisteError(ConciliacionError):
    """Error cuando ya existe una conciliación para el período"""
    
    def __init__(self, empresa_id: int, periodo: str):
        message = f"Ya existe conciliación para empresa {empresa_id} en período {periodo}"
        super().__init__(
            message, 
            "CONCILIACION_EXISTS", 
            {"empresa_id": empresa_id, "periodo": periodo}
        )


class ArchivoYaProcesadoError(ConciliacionError):
    """Error cuando el archivo ya fue procesado anteriormente"""
    
    def __init__(self, hash_archivo: str, archivo_existente_id: Optional[int] = None):
        message = f"El archivo ya fue procesado anteriormente (hash: {hash_archivo[:8]}...)"
        details = {"hash_archivo": hash_archivo}
        if archivo_existente_id:
            details["archivo_existente_id"] = archivo_existente_id
        super().__init__(message, "ARCHIVO_DUPLICADO", details)


class DatosInsuficientesError(ConciliacionError):
    """Error cuando no hay suficientes datos para conciliar"""
    
    def __init__(self, motivo: str):
        message = f"Datos insuficientes para conciliación: {motivo}"
        super().__init__(message, "DATOS_INSUFICIENTES", {"motivo": motivo})


class ConfiguracionInvalidaError(ConciliacionError):
    """Error en la configuración del sistema"""
    
    def __init__(self, parametro: str, valor_actual: Any, valor_esperado: str):
        message = f"Configuración inválida para {parametro}: {valor_actual}. Esperado: {valor_esperado}"
        super().__init__(
            message, 
            "CONFIG_INVALID", 
            {
                "parametro": parametro,
                "valor_actual": valor_actual,
                "valor_esperado": valor_esperado
            }
        )


class TimeoutError(ConciliacionError):
    """Error por timeout en operaciones"""
    
    def __init__(self, operacion: str, timeout_segundos: int):
        message = f"Timeout en operación '{operacion}' después de {timeout_segundos} segundos"
        super().__init__(
            message, 
            "TIMEOUT", 
            {"operacion": operacion, "timeout_segundos": timeout_segundos}
        )


class ValidacionDatosError(ConciliacionError):
    """Error de validación de datos"""
    
    def __init__(self, campo: str, valor: Any, regla: str):
        message = f"Error de validación en campo '{campo}': {regla}"
        super().__init__(
            message, 
            "VALIDATION_ERROR", 
            {"campo": campo, "valor": valor, "regla": regla}
        )


class ConciliacionManualRequeridaError(ConciliacionError):
    """Error cuando se requiere intervención manual"""
    
    def __init__(self, movimiento_id: int, razon: str):
        message = f"Se requiere conciliación manual para movimiento {movimiento_id}: {razon}"
        super().__init__(
            message, 
            "MANUAL_REQUIRED", 
            {"movimiento_id": movimiento_id, "razon": razon}
        )


class DatabaseError(ConciliacionError):
    """Error de base de datos"""
    
    def __init__(self, operation: str, original_error: str):
        message = f"Error de base de datos en operación '{operation}': {original_error}"
        super().__init__(
            message, 
            "DATABASE_ERROR", 
            {"operation": operation, "original_error": original_error}
        )


class ExternalServiceError(ConciliacionError):
    """Error en servicios externos (OpenAI, etc.)"""
    
    def __init__(self, service: str, error_message: str, status_code: Optional[int] = None):
        message = f"Error en servicio externo '{service}': {error_message}"
        details = {"service": service, "error_message": error_message}
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


class RateLimitError(ExternalServiceError):
    """Error por límite de rate en APIs externas"""
    
    def __init__(self, service: str, retry_after: Optional[int] = None):
        message = f"Límite de rate alcanzado para servicio '{service}'"
        details = {"service": service}
        if retry_after:
            details["retry_after"] = retry_after
            message += f". Reintentar después de {retry_after} segundos"
        super().__init__(service, message)


class InsufficientPermissionsError(ConciliacionError):
    """Error de permisos insuficientes"""
    
    def __init__(self, user_id: Optional[str] = None, action: Optional[str] = None):
        message = "Permisos insuficientes para realizar la operación"
        details = {}
        if user_id:
            details["user_id"] = user_id
        if action:
            details["action"] = action
            message += f": {action}"
        super().__init__(message, "INSUFFICIENT_PERMISSIONS", details)


# === HELPER FUNCTIONS ===

def handle_openai_error(error: Exception, context: str = "OpenAI API") -> OCRError:
    """
    Convierte errores de OpenAI en OCRError específicos
    """
    error_message = str(error)
    
    if "rate limit" in error_message.lower():
        return RateLimitError("OpenAI", extract_retry_after(error_message))
    elif "timeout" in error_message.lower():
        return TimeoutError("OpenAI API", 30)
    elif "authentication" in error_message.lower():
        return ConfiguracionInvalidaError("OPENAI_API_KEY", "***", "clave API válida")
    else:
        return ExternalServiceError("OpenAI", error_message)


def extract_retry_after(error_message: str) -> Optional[int]:
    """
    Extrae el tiempo de retry-after de mensajes de error de rate limit
    """
    import re
    match = re.search(r'retry after (\d+)', error_message.lower())
    if match:
        return int(match.group(1))
    return None


def handle_database_error(error: Exception, operation: str) -> DatabaseError:
    """
    Convierte errores de base de datos en DatabaseError
    """
    return DatabaseError(operation, str(error))


# === EXCEPTION MAPPER ===

EXCEPTION_STATUS_CODES = {
    EmpresaNoEncontradaError: 404,
    MovimientoNoEncontradoError: 404,
    CFDINoEncontradoError: 404,
    ConciliacionYaExisteError: 409,
    ArchivoYaProcesadoError: 409,
    ValidacionDatosError: 422,
    ConfiguracionInvalidaError: 500,
    DatabaseError: 500,
    ExternalServiceError: 502,
    RateLimitError: 429,
    TimeoutError: 504,
    InsufficientPermissionsError: 403,
    DatosInsuficientesError: 422,
    ConciliacionManualRequeridaError: 422,
    # Errores OCR
    OCRError: 422,
    PDFProcessingError: 422,
    BancoNoReconocidoError: 422,
    FormatoBancarioInvalidoError: 422,
    # Base
    ConciliacionError: 500
}


def get_http_status_code(exception: ConciliacionError) -> int:
    """
    Obtiene el código de estado HTTP apropiado para una excepción
    """
    return EXCEPTION_STATUS_CODES.get(type(exception), 500) 