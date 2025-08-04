# Módulo de Conciliación Bancaria Avanzada

Sistema avanzado de conciliación bancaria que utiliza OCR con OpenAI Vision API para procesar estados de cuenta y conciliar automáticamente con CFDIs existentes.

## 🚀 Características Principales

### ✨ OCR Avanzado
- **OpenAI Vision API (gpt-4o)** para máxima precisión
- **Detección automática de bancos mexicanos** (BBVA, Santander, Banamex, etc.)
- **Extracción inteligente** de movimientos, fechas, montos y referencias
- **Validación y limpieza** automática de datos extraídos

### 🎯 Algoritmo de Conciliación Ultra-Preciso
Implementa **6 estrategias** de conciliación con diferentes niveles de confianza:

1. **Match Exacto** (95% confianza) - Monto exacto + fecha ±3 días
2. **Match por Referencia** (90% confianza) - UUID/folio/serie en referencia bancaria
3. **Match Aproximado** (80% confianza) - Tolerancia configurable en monto y fecha
4. **Complementos de Pago PPD** (90% confianza) - Suma pagos parciales
5. **Heurística Combinada** (85% confianza) - Scoring ponderado multifactor
6. **Patrones ML** (70% confianza) - Análisis de patrones históricos

### 📊 Sistema de Alertas y Reportes
- **Alertas críticas** automáticas para movimientos significativos
- **Sugerencias inteligentes** para conciliación manual
- **Estadísticas detalladas** por período y método
- **Reportes completos** con métricas de calidad

## 📦 Instalación

### 1. Dependencias Requeridas

```bash
# Instalar dependencias del módulo
uv add PyMuPDF pillow openai

# O usando pip
pip install PyMuPDF pillow openai
```

### 2. Variables de Entorno

Agregar a tu archivo `.env`:

```env
# OpenAI API Key (requerida)
OPENAI_API_KEY=tu_clave_openai_aqui

# Configuraciones opcionales
CONCILIACION_TOLERANCIA_MONTO=1.00
CONCILIACION_DIAS_TOLERANCIA=3
CONCILIACION_MAX_FILE_SIZE=52428800  # 50MB
```

### 3. Migraciones de Base de Datos

```bash
# Crear las nuevas tablas del módulo
python -c "
from app.core.database import engine
from app.conciliacion.models import Base
Base.metadata.create_all(bind=engine)
print('✅ Tablas de conciliación creadas')
"
```

## 🛠️ Uso del Sistema

### API Endpoints Disponibles

El módulo expone los siguientes endpoints bajo `/api/v1/conciliacion`:

#### 📤 Subir Estado de Cuenta
```http
POST /api/v1/conciliacion/subir-estado-cuenta
Content-Type: multipart/form-data

# Parámetros:
# - rfc_empresa: RFC de la empresa (query)
# - file: Archivo PDF del estado de cuenta
```

#### ⚡ Ejecutar Conciliación
```http
POST /api/v1/conciliacion/ejecutar
Content-Type: application/json

{
  "rfc_empresa": "ABC123456789",
  "mes": 1,
  "anio": 2024,
  "tolerancia_monto": 1.00,
  "dias_tolerancia": 3,
  "forzar_reproceso": false
}
```

#### 📊 Obtener Reporte
```http
GET /api/v1/conciliacion/reporte/{empresa_id}?mes=1&anio=2024
```

#### 📋 Listar Movimientos
```http
GET /api/v1/conciliacion/movimientos/{empresa_id}
  ?estado=pendiente
  &tipo=cargo
  &fecha_inicio=2024-01-01
  &fecha_fin=2024-01-31
  &page=1
  &size=50
```

### Ejemplo de Uso Completo

```python
import requests
from datetime import datetime

# 1. Subir estado de cuenta
with open("estado_cuenta_enero.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/conciliacion/subir-estado-cuenta",
        params={"rfc_empresa": "ABC123456789"},
        files={"file": f}
    )
    resultado_ocr = response.json()
    print(f"✅ Movimientos extraídos: {resultado_ocr['total_movimientos_extraidos']}")

# 2. Ejecutar conciliación
response = requests.post(
    "http://localhost:8000/api/v1/conciliacion/ejecutar",
    json={
        "rfc_empresa": "ABC123456789",
        "mes": 1,
        "anio": 2024,
        "tolerancia_monto": 1.00,
        "dias_tolerancia": 3
    }
)
resultado_conciliacion = response.json()
print(f"📈 Porcentaje conciliado: {resultado_conciliacion['estadisticas']['porcentaje_conciliacion']:.2f}%")

# 3. Obtener reporte
response = requests.get(
    f"http://localhost:8000/api/v1/conciliacion/reporte/1",
    params={"mes": 1, "anio": 2024}
)
reporte = response.json()
print(f"📋 Movimientos pendientes: {len(reporte['movimientos_pendientes'])}")
```

## ⚙️ Configuración Avanzada

### Configuración por Banco

El sistema incluye configuraciones específicas para cada banco mexicano:

```python
# En ocr_processor.py
CONFIGURACIONES_BANCO = {
    "bbva": {
        "formatos_fecha": ["%d/%m/%Y", "%d-%m-%Y"],
        "patrones_referencia": [r"REF\s*\d+", r"AUT\s*\d+"],
        "tolerancia_monto": Decimal('0.50')
    },
    "santander": {
        "formatos_fecha": ["%d/%m/%Y", "%d-%m-%Y"], 
        "patrones_referencia": [r"OP\s*\d+", r"MOV\s*\d+"],
        "tolerancia_monto": Decimal('1.00')
    }
    # ... más bancos
}
```

### Ajustar Tolerancias de Conciliación

```python
# En conciliador.py
config = {
    "tolerancia_monto_default": Decimal('1.00'),  # Pesos mexicanos
    "dias_tolerancia_default": 3,                  # Días
    "score_minimo_confianza": 0.7,                # 0.0 a 1.0
    "max_sugerencias_por_movimiento": 3
}
```

## 🧪 Testing

El módulo incluye tests completos para todas las funcionalidades:

```bash
# Ejecutar todos los tests
pytest app/conciliacion/tests/ -v

# Tests específicos
pytest app/conciliacion/tests/test_conciliacion.py -v
pytest app/conciliacion/tests/test_ocr.py -v

# Con cobertura
pytest app/conciliacion/tests/ --cov=app.conciliacion --cov-report=html
```

### Fixtures de Prueba

El directorio `tests/fixtures/` puede contener PDFs de ejemplo para testing:

```
tests/fixtures/
├── bbva_enero_2024.pdf
├── santander_febrero_2024.pdf
└── banamex_marzo_2024.pdf
```

## 📈 Monitoreo y Performance

### Métricas Clave

El sistema genera métricas detalladas:

- **Tasa de conciliación** por período y empresa
- **Tiempo de procesamiento** de OCR y conciliación
- **Distribución por métodos** de conciliación
- **Alertas críticas** y patrones de error

### Logging Estructurado

```python
# Ejemplo de logs generados
2024-01-15 10:30:00 - conciliacion.ocr - INFO - OCR completado: 45 movimientos en 12.34s
2024-01-15 10:30:15 - conciliacion.conciliador - INFO - Conciliación completada en 3.21s: 94.67% éxito
2024-01-15 10:30:16 - conciliacion.router - WARNING - Movimiento de $15,000.00 sin conciliar
```

### Optimizaciones de Performance

- **Caché de CFDIs** precargados por período
- **Queries optimizadas** con índices específicos
- **Processing en batch** para múltiples movimientos
- **Rate limiting** automático para APIs externas

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. Error "OPENAI_API_KEY es requerida"
```bash
# Verificar variable de entorno
echo $OPENAI_API_KEY

# Agregar al .env
echo "OPENAI_API_KEY=tu_clave_aqui" >> .env
```

#### 2. Error "No se pudo identificar el banco"
- Verificar que el PDF sea un estado de cuenta válido
- Revisar que el banco esté soportado (BBVA, Santander, Banamex, etc.)
- Contactar soporte si es un banco nuevo

#### 3. Baja tasa de conciliación
- Ajustar `tolerancia_monto` y `dias_tolerancia`
- Verificar que los CFDIs estén en el período correcto
- Revisar alertas críticas para patrones de error

#### 4. Error de memoria con PDFs grandes
- Reducir `MAX_FILE_SIZE` en la configuración
- Procesar PDFs por lotes más pequeños
- Optimizar resolución de imágenes en OCR

### Logs de Debug

```bash
# Habilitar logging detallado
export LOG_LEVEL=DEBUG

# Ver logs específicos del módulo
tail -f logs/conciliacion.log | grep "conciliacion"
```

## 🔐 Seguridad

### Consideraciones de Seguridad

- **API Keys protegidas** - Nunca hardcodear claves
- **Validación estricta** de archivos PDF
- **Sanitización** de datos extraídos
- **Rate limiting** en endpoints públicos
- **Logging seguro** - No loguear datos sensibles

### Archivos Temporales

El sistema no almacena archivos PDF en disco, todo el procesamiento se hace en memoria para mayor seguridad.

## 🤝 Contribución

### Estructura del Código

```
app/conciliacion/
├── __init__.py           # Módulo principal
├── models.py            # Modelos SQLAlchemy
├── schemas.py           # Schemas Pydantic  
├── router.py            # Endpoints FastAPI
├── conciliador.py       # Algoritmo de conciliación
├── ocr_processor.py     # Procesador OCR
├── utils.py             # Funciones auxiliares
├── exceptions.py        # Excepciones personalizadas
├── tests/               # Tests unitarios
│   ├── __init__.py
│   ├── test_conciliacion.py
│   ├── test_ocr.py
│   └── fixtures/        # PDFs de prueba
└── README.md           # Esta documentación
```

### Agregar Soporte para Nuevo Banco

1. **Actualizar enum de bancos** en `models.py`:
```python
class TipoBanco(PyEnum):
    # ... bancos existentes
    NUEVO_BANCO = "nuevo_banco"
```

2. **Agregar configuración** en `ocr_processor.py`:
```python
configuraciones = {
    # ... configuraciones existentes
    "nuevo_banco": {
        "formatos_fecha": ["%d/%m/%Y"],
        "patrones_referencia": [r"REF\s*\d+"],
        "tolerancia_monto": Decimal('1.00')
    }
}
```

3. **Actualizar detección** en prompts de OpenAI
4. **Agregar tests** específicos para el nuevo banco

## 📄 Licencia

Este módulo es parte del sistema AsistenteFiscal.AI y está sujeto a la misma licencia del proyecto principal.

## 🆘 Soporte

Para soporte técnico:
- 📧 Email: soporte@asistente-fiscal.ai
- 📚 Documentación: `/docs` endpoint
- 🐛 Issues: GitHub repository

---

**Versión:** 1.0.0  
**Última actualización:** Enero 2024  
**Compatibilidad:** Python 3.8+ | FastAPI 0.68+ | SQLAlchemy 1.4+ 