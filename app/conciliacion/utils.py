"""
Funciones auxiliares para el módulo de conciliación bancaria avanzada

Contiene utilidades críticas para procesamiento de texto, validaciones,
cálculos y operaciones comunes del módulo
"""

import re
import hashlib
import difflib
from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import unicodedata
import logging

logger = logging.getLogger(__name__)


# === FUNCIONES DE TEXTO ===

def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto para comparaciones consistentes
    
    Args:
        texto: Texto a normalizar
        
    Returns:
        Texto normalizado y limpio
    """
    if not texto:
        return ""
    
    # Convertir a minúsculas
    texto = texto.lower()
    
    # Normalizar unicode (remover acentos)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    
    # Remover caracteres especiales excepto números, letras y espacios
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    
    # Remover espacios múltiples
    texto = re.sub(r'\s+', ' ', texto)
    
    # Trim
    return texto.strip()


def limpiar_concepto_bancario(concepto: str) -> str:
    """
    Limpia conceptos bancarios removiendo prefijos comunes y normalizando
    
    Args:
        concepto: Concepto bancario original
        
    Returns:
        Concepto limpio para comparación
    """
    if not concepto:
        return ""
    
    concepto_limpio = normalizar_texto(concepto)
    
    # Prefijos comunes a remover
    prefijos_remover = [
        r'^pago\s+',                  # "PAGO FACTURA"
        r'^transferencia\s+',         # "TRANSFERENCIA A"
        r'^deposito\s+',              # "DEPOSITO DE"
        r'^retiro\s+',                # "RETIRO DE"
        r'^cargo\s+',                 # "CARGO POR"
        r'^abono\s+',                 # "ABONO DE"
        r'^comision\s+',              # "COMISION POR"
        r'^interes\s+',               # "INTERES SOBRE"
        r'^ref\s*\d+\s*',            # "REF 123456"
        r'^operacion\s*\d+\s*',      # "OPERACION 789"
        r'^\d{2}/\d{2}/\d{4}\s*',    # Fechas al inicio
    ]
    
    for patron in prefijos_remover:
        concepto_limpio = re.sub(patron, '', concepto_limpio)
    
    return concepto_limpio.strip()


def extraer_rfc_de_texto(texto: str) -> List[str]:
    """
    Extrae posibles RFCs de un texto
    
    Args:
        texto: Texto donde buscar RFCs
        
    Returns:
        Lista de RFCs encontrados
    """
    if not texto:
        return []
    
    # Patrones RFC
    patron_fisica = r'\b[A-Z&Ñ]{4}[0-9]{6}[A-Z0-9]{3}\b'
    patron_moral = r'\b[A-Z&Ñ]{3}[0-9]{6}[A-Z0-9]{3}\b'
    
    texto_upper = texto.upper()
    rfcs = []
    
    # Buscar RFCs de personas físicas
    rfcs.extend(re.findall(patron_fisica, texto_upper))
    
    # Buscar RFCs de personas morales
    rfcs.extend(re.findall(patron_moral, texto_upper))
    
    # Remover duplicados manteniendo orden
    return list(dict.fromkeys(rfcs))


def extraer_numeros(texto: str) -> List[Decimal]:
    """
    Extrae números decimales de un texto
    
    Args:
        texto: Texto donde buscar números
        
    Returns:
        Lista de números encontrados como Decimal
    """
    if not texto:
        return []
    
    # Patrones para números con decimales
    patrones = [
        r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56 o 1,234.56
        r'\$?\s*(\d+\.\d{2})',                       # $123.45 o 123.45
        r'\$?\s*(\d+)',                              # $123 o 123
    ]
    
    numeros = []
    
    for patron in patrones:
        matches = re.findall(patron, texto)
        for match in matches:
            try:
                # Remover comas para convertir
                numero_str = match.replace(',', '')
                numero = Decimal(numero_str)
                numeros.append(numero)
            except (ValueError, TypeError):
                continue
    
    return numeros


def calcular_similitud_texto(texto1: str, texto2: str) -> float:
    """
    Calcula similitud entre dos textos usando difflib
    
    Args:
        texto1: Primer texto
        texto2: Segundo texto
        
    Returns:
        Similitud entre 0.0 y 1.0
    """
    if not texto1 or not texto2:
        return 0.0
    
    # Normalizar ambos textos
    t1_norm = normalizar_texto(texto1)
    t2_norm = normalizar_texto(texto2)
    
    if not t1_norm or not t2_norm:
        return 0.0
    
    # Usar SequenceMatcher para similitud
    matcher = difflib.SequenceMatcher(None, t1_norm, t2_norm)
    return matcher.ratio()


def extraer_folios_serie(texto: str) -> Dict[str, str]:
    """
    Extrae posibles folios y series de CFDIs de un texto
    
    Args:
        texto: Texto donde buscar folios/series
        
    Returns:
        Diccionario con folios y series encontrados
    """
    resultado = {"folios": [], "series": []}
    
    if not texto:
        return resultado
    
    texto_upper = texto.upper()
    
    # Patrones para folios (números)
    folios = re.findall(r'\b\d{4,8}\b', texto_upper)
    resultado["folios"] = list(set(folios))
    
    # Patrones para series (letras + números)
    series = re.findall(r'\b[A-Z]{1,5}\d{1,8}\b', texto_upper)
    resultado["series"] = list(set(series))
    
    return resultado


# === FUNCIONES DE VALIDACIÓN ===

def validar_rfc(rfc: str) -> bool:
    """
    Valida formato de RFC mexicano
    
    Args:
        rfc: RFC a validar
        
    Returns:
        True si es válido, False en caso contrario
    """
    if not rfc:
        return False
    
    rfc = rfc.upper().strip()
    
    # Patrones RFC
    patron_fisica = r'^[A-Z&Ñ]{4}[0-9]{6}[A-Z0-9]{3}$'
    patron_moral = r'^[A-Z&Ñ]{3}[0-9]{6}[A-Z0-9]{3}$'
    
    return bool(re.match(patron_fisica, rfc) or re.match(patron_moral, rfc))


def validar_uuid(uuid: str) -> bool:
    """
    Valida formato de UUID
    
    Args:
        uuid: UUID a validar
        
    Returns:
        True si es válido, False en caso contrario
    """
    if not uuid or len(uuid) != 36:
        return False
    
    patron_uuid = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    return bool(re.match(patron_uuid, uuid))


# === FUNCIONES DE CÁLCULO ===

def comparar_montos(monto1: Decimal, monto2: Decimal, tolerancia: Decimal = Decimal('1.00')) -> Dict[str, Any]:
    """
    Compara dos montos con tolerancia configurable
    
    Args:
        monto1: Primer monto
        monto2: Segundo monto
        tolerancia: Tolerancia permitida
        
    Returns:
        Diccionario con resultado de comparación
    """
    if monto1 is None or monto2 is None:
        return {
            "exacto": False,
            "aproximado": False,
            "diferencia": None,
            "porcentaje_diferencia": None,
            "dentro_tolerancia": False
        }
    
    # Redondear a 2 decimales
    m1 = monto1.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    m2 = monto2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    diferencia = abs(m1 - m2)
    exacto = diferencia == Decimal('0.00')
    dentro_tolerancia = diferencia <= tolerancia
    
    # Calcular porcentaje de diferencia
    monto_base = max(m1, m2)
    porcentaje_diferencia = None
    if monto_base > 0:
        porcentaje_diferencia = float((diferencia / monto_base) * 100)
    
    return {
        "exacto": exacto,
        "aproximado": dentro_tolerancia and not exacto,
        "diferencia": diferencia,
        "porcentaje_diferencia": porcentaje_diferencia,
        "dentro_tolerancia": dentro_tolerancia
    }


def calcular_rango_fechas(mes: int, anio: int) -> Tuple[datetime, datetime]:
    """
    Calcula rango de fechas para un mes/año específico
    
    Args:
        mes: Mes (1-12)
        anio: Año
        
    Returns:
        Tupla con fecha inicio y fecha fin del período
    """
    if not (1 <= mes <= 12):
        raise ValueError("Mes debe estar entre 1 y 12")
    
    if not (2000 <= anio <= 2030):
        raise ValueError("Año debe estar entre 2000 y 2030")
    
    # Primer día del mes
    fecha_inicio = datetime(anio, mes, 1)
    
    # Último día del mes
    if mes == 12:
        fecha_fin = datetime(anio + 1, 1, 1) - timedelta(days=1)
    else:
        fecha_fin = datetime(anio, mes + 1, 1) - timedelta(days=1)
    
    # Ajustar a fin del día
    fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
    
    return fecha_inicio, fecha_fin


def esta_en_rango_fechas(fecha: datetime, fecha_base: datetime, dias_tolerancia: int = 3) -> bool:
    """
    Verifica si una fecha está dentro del rango de tolerancia de otra fecha
    
    Args:
        fecha: Fecha a verificar
        fecha_base: Fecha de referencia
        dias_tolerancia: Días de tolerancia
        
    Returns:
        True si está en rango, False en caso contrario
    """
    if not fecha or not fecha_base:
        return False
    
    diferencia = abs((fecha - fecha_base).days)
    return diferencia <= dias_tolerancia


def calcular_score_fecha(fecha1: datetime, fecha2: datetime, max_dias: int = 30) -> float:
    """
    Calcula score de similitud entre fechas (1.0 = exacto, 0.0 = muy diferente)
    
    Args:
        fecha1: Primera fecha
        fecha2: Segunda fecha
        max_dias: Máximo de días para score 0
        
    Returns:
        Score entre 0.0 y 1.0
    """
    if not fecha1 or not fecha2:
        return 0.0
    
    diferencia_dias = abs((fecha1 - fecha2).days)
    
    if diferencia_dias == 0:
        return 1.0
    elif diferencia_dias >= max_dias:
        return 0.0
    else:
        return 1.0 - (diferencia_dias / max_dias)


# === FUNCIONES DE HASH Y ARCHIVOS ===

def calcular_hash_archivo(contenido_bytes: bytes) -> str:
    """
    Calcula hash SHA-256 de un archivo
    
    Args:
        contenido_bytes: Contenido del archivo en bytes
        
    Returns:
        Hash SHA-256 en hexadecimal
    """
    return hashlib.sha256(contenido_bytes).hexdigest()


def generar_clave_unica(elementos: List[str]) -> str:
    """
    Genera una clave única a partir de elementos
    
    Args:
        elementos: Lista de elementos para generar clave
        
    Returns:
        Clave única
    """
    texto_completo = "|".join(str(elem) for elem in elementos)
    return hashlib.md5(texto_completo.encode()).hexdigest()[:16]


# === FUNCIONES DE FORMATEO ===

def formatear_monto(monto: Decimal) -> str:
    """
    Formatea un monto como currency mexicano
    
    Args:
        monto: Monto a formatear
        
    Returns:
        Monto formateado como string
    """
    if monto is None:
        return "$0.00"
    
    monto_redondeado = monto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"${monto_redondeado:,.2f}"


def formatear_porcentaje(valor: float) -> str:
    """
    Formatea un valor como porcentaje
    
    Args:
        valor: Valor entre 0 y 1
        
    Returns:
        Porcentaje formateado
    """
    if valor is None:
        return "0.00%"
    
    return f"{valor * 100:.2f}%"


def truncar_texto(texto: str, longitud: int = 50) -> str:
    """
    Trunca texto a longitud especificada
    
    Args:
        texto: Texto a truncar
        longitud: Longitud máxima
        
    Returns:
        Texto truncado
    """
    if not texto:
        return ""
    
    if len(texto) <= longitud:
        return texto
    
    return texto[:longitud-3] + "..."


# === FUNCIONES DE LOGGING ===

def log_operacion(operacion: str, parametros: Dict[str, Any], resultado: bool, tiempo_ms: int):
    """
    Registra operación en logs con formato estructurado
    
    Args:
        operacion: Nombre de la operación
        parametros: Parámetros de la operación
        resultado: Si fue exitosa
        tiempo_ms: Tiempo en milisegundos
    """
    nivel = logging.INFO if resultado else logging.WARNING
    
    log_data = {
        "operacion": operacion,
        "parametros": parametros,
        "exito": resultado,
        "tiempo_ms": tiempo_ms
    }
    
    logger.log(nivel, f"Operación {operacion}: {'EXITOSA' if resultado else 'FALLIDA'}", extra=log_data)


# === FUNCIONES DE CONFIGURACIÓN ===

def obtener_configuracion_banco(banco_codigo: str) -> Dict[str, Any]:
    """
    Obtiene configuración específica por banco
    
    Args:
        banco_codigo: Código del banco
        
    Returns:
        Configuración del banco
    """
    configuraciones = {
        "bbva": {
            "patrones_fecha": [r'\d{2}/\d{2}/\d{4}', r'\d{4}-\d{2}-\d{2}'],
            "prefijos_concepto": ["PAGO ", "TRANSFERENCIA ", "CARGO "],
            "tolerancia_monto": Decimal('0.50'),
            "campos_referencia": ["referencia", "folio", "autorizacion"]
        },
        "santander": {
            "patrones_fecha": [r'\d{2}-\d{2}-\d{4}', r'\d{2}/\d{2}/\d{4}'],
            "prefijos_concepto": ["OPERACION ", "MOV ", "REF "],
            "tolerancia_monto": Decimal('1.00'),
            "campos_referencia": ["numero_operacion", "referencia"]
        },
        "banamex": {
            "patrones_fecha": [r'\d{2}/\d{2}/\d{2}', r'\d{2}/\d{2}/\d{4}'],
            "prefijos_concepto": ["TRF ", "DEP ", "RET "],
            "tolerancia_monto": Decimal('0.01'),
            "campos_referencia": ["folio", "referencia", "operacion"]
        }
    }
    
    return configuraciones.get(banco_codigo.lower(), configuraciones["bbva"])


# === CONSTANTES ===

TOLERANCIA_MONTO_DEFAULT = Decimal('1.00')
DIAS_TOLERANCIA_DEFAULT = 3
MAX_LONGITUD_CONCEPTO = 1000
SCORE_MINIMO_CONFIANZA = 0.7

# Patrones comunes
PATRON_RFC_FISICA = r'^[A-Z&Ñ]{4}[0-9]{6}[A-Z0-9]{3}$'
PATRON_RFC_MORAL = r'^[A-Z&Ñ]{3}[0-9]{6}[A-Z0-9]{3}$'
PATRON_UUID = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' 