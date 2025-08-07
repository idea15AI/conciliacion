# Sistema de Conciliación Bancaria

Sistema avanzado de conciliación bancaria que utiliza **Google Gemini API** para procesar estados de cuenta bancarios y extraer movimientos automáticamente.

## 🚀 Características Principales

### ✨ Procesamiento Inteligente de PDFs
- **Google Gemini API** para máxima precisión
- **Detección automática de bancos mexicanos** (BBVA, Santander, Banorte, Inbursa)
- **Extracción inteligente** de movimientos, fechas, montos y referencias
- **Validación y limpieza** automática de datos extraídos

### 🎯 Bancos Soportados
- **BBVA**: Formato con códigos BNET y SPEI
- **Santander**: Estados de cuenta PYME
- **Banorte**: Movimientos con DEPOSITO/RETIRO
- **Inbursa**: Estados con TASA DE DESCTO y LIQUIDACION

### 📊 Interfaz Web Simple
- **Procesamiento directo** de PDFs bancarios
- **Visualización de movimientos** en tabla
- **Descarga de resultados** en JSON
- **Interfaz minimalista** y fácil de usar

## ⚡ Uso Rápido

### 1. Iniciar Servidor
```bash
uvicorn app.core.main:app --reload --port 8000
```

### 2. Acceder a la Interfaz
- Abrir: http://localhost:8000/simple-interface
- Subir PDF de estado de cuenta bancario
- Ver movimientos extraídos en tabla

### 3. Usar API Directamente
```bash
curl -X POST "http://localhost:8000/api/v1/procesar-pdf/subir?empresa_id=1" \
  -F "file=@estado_cuenta.pdf"
```

## 📦 Instalación

### 1. Requisitos del Sistema
- Python 3.9 o superior
- MySQL 8.0 o superior
- Google Gemini API Key

### 2. Instalar Dependencias

```bash
# Instalar usando uv (recomendado)
uv install

# O usando pip
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno

Crear archivo `.env` basado en el ejemplo:

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar con tus configuraciones
nano .env  # o usar tu editor preferido
```

Configuraciones principales en `.env`:

```env
# Base de datos MySQL
DB_MSQL_USERNAME=root
DB_MSQL_PASSWORD=tu_password
DB_MSQL_DATABASE=alertadefinitivo
DB_MSQL_HOST=localhost
DB_MSQL_PORT=3306

# Google Gemini API Key (requerida para procesamiento)
GEMINI_API_KEY=tu_clave_gemini_aqui

# Configuración de CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

**⚠️ IMPORTANTE:** Necesitas una API Key de Google Gemini para procesar los PDFs.

### 4. Configurar Base de Datos

```bash
# Crear las tablas necesarias
python scripts/create_conciliacion_tables.py
```

## 🚀 Uso del Sistema

### 1. Iniciar el Servidor

```bash
# Usando uv (recomendado)
uv run uvicorn app.core.main:app --reload --port 8000

# O usando uvicorn directamente
uvicorn app.core.main:app --reload --port 8000
```

### 2. Acceder al Sistema

- **Interfaz Web**: http://localhost:8000/simple-interface
- **API Docs**: http://localhost:8000/docs
- **API**: http://localhost:8000/api/v1/procesar-pdf/subir

## 📖 Documentación Detallada

Para documentación completa del módulo de conciliación, ver:
- [README de Conciliación](app/conciliacion/README.md) - Documentación técnica detallada
- [Documentación API](http://localhost:8000/docs) - Endpoints interactivos

## 🛠️ API Endpoints Principales

### Procesar PDF Bancario
```http
POST /api/v1/procesar-pdf/subir?empresa_id=1
Content-Type: multipart/form-data

# Parámetros:
# - empresa_id: ID de la empresa (query parameter)
# - file: Archivo PDF del estado de cuenta bancario

# Respuesta:
{
  "id": 123,
  "empresa_id": 1,
  "nombre_archivo": "estado_cuenta.pdf",
  "banco": "BBVA",
  "total_movimientos": 25,
  "movimientos_procesados": 25,
  "procesado_exitosamente": true,
  "fecha_creacion": "2025-01-15T10:30:00",
  "fecha_procesamiento": "2025-01-15T10:30:05",
  "tiempo_procesamiento": 5,
  "resultado_procesamiento": {
    "exito": true,
    "mensaje": "PDF procesado exitosamente: 25 movimientos extraídos",
    "banco_detectado": "BBVA",
    "total_movimientos_extraidos": 25,
    "movimientos": [
      {
        "fecha": "2025-01-15",
        "concepto": "SPEI ENVIADO BANREGIO",
        "referencia": "BNET01002506200029230973",
        "cargos": 2000.00,
        "abonos": null,
        "saldo": 50000.00,
        "tipo": "CARGO",
        "estado": "PENDIENTE"
      }
    ],
    "modelo_utilizado": "gemini-2.5-flash-lite",
    "tiempo_procesamiento_segundos": 5.2
  }
}
```

### Obtener Movimientos de Archivo
```http
GET /api/v1/procesar-pdf/archivo/{archivo_id}

# Respuesta:
{
  "id": 123,
  "empresa_id": 1,
  "nombre_archivo": "estado_cuenta.pdf",
  "banco": "BBVA",
  "total_movimientos": 25,
  "movimientos_procesados": 25,
  "procesado_exitosamente": true,
  "resultado_procesamiento": {
    "movimientos": [...]
  }
}
```

### Listar Archivos de Empresa
```http
GET /api/v1/procesar-pdf/empresa/{empresa_id}

# Respuesta:
[
  {
    "id": 123,
    "nombre_archivo": "estado_cuenta.pdf",
    "banco": "BBVA",
    "total_movimientos": 25,
    "procesado_exitosamente": true,
    "fecha_creacion": "2025-01-15T10:30:00"
  }
]
```

## 🧪 Testing

```bash
# Ejecutar tests del backend
pytest app/conciliacion/tests/ -v

# Con cobertura
pytest app/conciliacion/tests/ --cov=app.conciliacion --cov-report=html
```

## 🔧 Troubleshooting

### Problemas Comunes

1. **Error "GEMINI_API_KEY es requerida"**
   - Verificar que la variable esté configurada en `.env`
   - Obtener API Key en: https://makersuite.google.com/app/apikey

2. **Error de conexión a base de datos**
   - Verificar credenciales en `.env`
   - Asegurar que MySQL esté ejecutándose
   - Crear la base de datos si no existe

3. **Error al procesar PDF**
   - Verificar que el archivo sea un PDF válido
   - Máximo 50MB por archivo
   - Debe ser un estado de cuenta de banco soportado (BBVA, Santander, Banorte, Inbursa)

4. **Detección incorrecta de banco**
   - El sistema detecta automáticamente el banco
   - Si detecta mal, verificar que el PDF sea del banco correcto
   - Los prompts están optimizados para cada banco específico
