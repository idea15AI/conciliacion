# Sistema de Conciliación Bancaria

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

### 1. Requisitos del Sistema
- Python 3.11 o superior
- Node.js 18 o superior (para el frontend)
- MySQL 8.0 o superior
- OpenAI API Key

### 2. Instalar Dependencias Backend

```bash
# Instalar usando uv (recomendado)
uv install

# O usando pip
pip install -r requirements.txt
```

### 3. Instalar Dependencias Frontend

```bash
cd frontend
npm install
```

### 4. Configuración de Variables de Entorno

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

# OpenAI API Key (requerida para OCR)
OPENAI_API_KEY=tu_clave_openai_aqui

# Configuraciones de conciliación
CONCILIACION_TOLERANCIA_MONTO=1.00
CONCILIACION_DIAS_TOLERANCIA=3
CONCILIACION_MAX_FILE_SIZE=52428800

# Configuración de CORS (incluye puertos alternativos)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3002,http://127.0.0.1:3002
```

**⚠️ IMPORTANTE:** El archivo `.env.example` contiene todas las variables disponibles con comentarios explicativos.

### 5. Configurar Base de Datos

```bash
# Crear las tablas necesarias
python scripts/create_conciliacion_tables.py
```

## 🚀 Uso del Sistema

### 1. Iniciar el Backend

```bash
# Usando uv (recomendado)
uv run uvicorn app.core.main:app --reload --port 8000

# O usando uvicorn directamente
uvicorn app.core.main:app --reload --port 8000
```

### 2. Iniciar el Frontend

```bash
cd frontend
npm run dev
```

### 3. Acceder al Sistema

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API**: http://localhost:8000/api/v1/conciliacion

## 📖 Documentación Detallada

Para documentación completa del módulo de conciliación, ver:
- [README de Conciliación](app/conciliacion/README.md) - Documentación técnica detallada
- [Documentación API](http://localhost:8000/docs) - Endpoints interactivos

## 🛠️ API Endpoints Principales

### Subir Estado de Cuenta
```http
POST /api/v1/conciliacion/subir-estado-cuenta
Content-Type: multipart/form-data

# Parámetros:
# - rfc_empresa: RFC de la empresa (query)
# - file: Archivo PDF del estado de cuenta
```

### Ejecutar Conciliación
```http
POST /api/v1/conciliacion/ejecutar
Content-Type: application/json

{
  "rfc_empresa": "ABC123456789",
  "mes": 1,
  "anio": 2024,
  "tolerancia_monto": 1.00,
  "dias_tolerancia": 3
}
```

### Obtener Reporte
```http
GET /api/v1/conciliacion/reporte/{empresa_id}?mes=1&anio=2024
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

1. **Error "OPENAI_API_KEY es requerida"**
   - Verificar que la variable esté configurada en `.env`
   - La clave debe tener permisos para usar Vision API

2. **Error de conexión a base de datos**
   - Verificar credenciales en `.env`
   - Asegurar que MySQL esté ejecutándose
   - Crear la base de datos si no existe

3. **Error al procesar PDF**
   - Verificar que el archivo sea un PDF válido
   - Máximo 50MB por archivo
   - Debe ser un estado de cuenta de banco soportado

## 🚦 Estado del Proyecto

- ✅ **Backend**: Módulo de conciliación completo y funcional
- ✅ **API**: Endpoints REST documentados
- ✅ **Frontend**: Interfaz básica para conciliación
- ✅ **OCR**: Integración con OpenAI Vision API
- ✅ **Base de Datos**: Modelos y migraciones
- ✅ **Tests**: Cobertura básica del módulo

## 📝 Licencia

Este proyecto está bajo licencia privada. Para más información, contactar al equipo de desarrollo.

## 🆘 Soporte

Para soporte técnico o preguntas:
- 📧 Email: soporte@conciliacion-bancaria.com
- 📚 Documentación: http://localhost:8000/docs
- 📖 Wiki: Ver carpeta `app/conciliacion/README.md`
