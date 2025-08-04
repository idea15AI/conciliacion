# 🛠️ Guía de Instalación - AsistenteFiscal.AI

Esta guía te llevará paso a paso para configurar AsistenteFiscal.AI en tu sistema.

## ⚡ Inicio Rápido

### 1. Prerrequisitos
Asegúrate de tener instalado:
- Python 3.12+
- Node.js 18+
- Docker y Docker Compose
- UV (gestor de dependencias Python)

### 2. Instalación de UV
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Configuración Inicial
```bash
# 1. Clonar repositorio
git clone <repository-url>
cd cfdi-inteligente

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 3. Levantar base de datos
cd docker
docker-compose up -d postgres

# 4. Instalar dependencias backend
cd ..
uv sync

# 5. Instalar dependencias frontend
cd frontend
npm install
```

### 4. Ejecutar el sistema
```bash
# Terminal 1: Backend
uv run python main.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

## 🔧 Configuración Detallada

### Variables de Entorno

Edita el archivo `.env` con tus configuraciones:

```env
# Base de datos PostgreSQL
DATABASE_URL=postgresql://postgres:password@localhost:5432/cfdi_inteligente
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cfdi_inteligente
DB_USER=postgres
DB_PASSWORD=password

# API Keys (configura al menos una)
OPENAI_API_KEY=sk-tu-openai-key-aqui
ANTHROPIC_API_KEY=sk-ant-tu-anthropic-key-aqui

# Configuración de la aplicación
APP_NAME=AsistenteFiscal.AI
APP_VERSION=1.0.0
DEBUG=True
SECRET_KEY=cambia-esta-clave-secreta

# CORS para frontend
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]

# Configuración de archivos
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_FOLDER=uploads/
ALLOWED_EXTENSIONS=["xml"]

# Configuración de IA
DEFAULT_MODEL_PROVIDER=openai  # o "anthropic"
DEFAULT_MODEL=gpt-4o-mini
LANGGRAPH_TIMEOUT=60
```

### Base de Datos PostgreSQL

El sistema usa PostgreSQL como base de datos principal. Puedes usar Docker o una instalación local.

#### Opción 1: Docker (Recomendado)
```bash
cd docker
docker-compose up -d postgres
```

#### Opción 2: Instalación Local
```bash
# Instalar PostgreSQL
brew install postgresql  # macOS
sudo apt-get install postgresql  # Ubuntu

# Crear base de datos
createdb cfdi_inteligente

# Configurar usuario
psql -c "CREATE USER cfdi_app WITH PASSWORD 'password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE cfdi_inteligente TO cfdi_app;"
```

### Configuración de IA

El sistema soporta OpenAI y Anthropic. Configura al menos uno:

#### OpenAI
1. Registrate en https://platform.openai.com/
2. Crea una API key
3. Configura `OPENAI_API_KEY` en `.env`

#### Anthropic
1. Registrate en https://console.anthropic.com/
2. Crea una API key
3. Configura `ANTHROPIC_API_KEY` en `.env`

## 🚀 Verificación de Instalación

### 1. Verificar Backend
```bash
# Verificar health check
curl http://localhost:8000/health

# Verificar documentación
open http://localhost:8000/docs
```

### 2. Verificar Frontend
```bash
# Abrir en navegador
open http://localhost:3000
```

### 3. Verificar Base de Datos
```bash
# Conectar a PostgreSQL
psql -h localhost -U postgres -d cfdi_inteligente

# Verificar tablas
\dt
```

## 🐛 Solución de Problemas

### Error: Conexión a base de datos

```bash
# Verificar que PostgreSQL esté corriendo
docker-compose ps

# Reiniciar contenedor
docker-compose restart postgres

# Verificar logs
docker-compose logs postgres
```

### Error: Dependencias Python

```bash
# Limpiar cache de UV
uv clean

# Reinstalar dependencias
uv sync --refresh
```

### Error: API Keys

```bash
# Verificar variables de entorno
echo $OPENAI_API_KEY

# Verificar configuración
uv run python -c "from app.core.config import settings; print(settings.OPENAI_API_KEY)"
```

### Error: Puerto ocupado

```bash
# Verificar puertos en uso
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
lsof -i :5432  # PostgreSQL

# Cambiar puerto si es necesario
uvicorn app.main:app --port 8001
```

## 📊 Validación del Sistema

### 1. Subir CFDI de Prueba

1. Ve a http://localhost:3000
2. Ingresa un RFC de prueba: `AAA010101AAA`
3. Arrastra un archivo XML CFDI válido
4. Verifica que se procese correctamente

### 2. Hacer Consulta IA

1. Ve a la pestaña "Consultas IA"
2. Haz una pregunta: "¿Cuántas facturas tengo?"
3. Verifica que obtengas una respuesta

### 3. Verificar Estadísticas

1. Ve a la pestaña "Estadísticas"
2. Verifica que se muestren datos del RFC

## 🔄 Actualizaciones

### Actualizar Dependencias Backend
```bash
uv sync --upgrade
```

### Actualizar Dependencias Frontend
```bash
cd frontend
npm update
```

### Actualizar Base de Datos
```bash
# Si hay cambios en el esquema
uv run alembic upgrade head
```

## 📋 Checklist de Instalación

- [ ] Python 3.12+ instalado
- [ ] Node.js 18+ instalado
- [ ] Docker y Docker Compose instalados
- [ ] UV instalado
- [ ] Repositorio clonado
- [ ] Variables de entorno configuradas
- [ ] PostgreSQL corriendo
- [ ] Dependencias backend instaladas
- [ ] Dependencias frontend instaladas
- [ ] Backend funcionando (http://localhost:8000)
- [ ] Frontend funcionando (http://localhost:3000)
- [ ] Base de datos conectada
- [ ] API keys configuradas
- [ ] Prueba de upload exitosa
- [ ] Consulta IA exitosa

## 🆘 Contacto

Si tienes problemas con la instalación:
- Revisa los logs del sistema
- Consulta la documentación completa
- Abre un issue en GitHub
- Contacta al equipo de desarrollo

---

¡Felicidades! Ya tienes AsistenteFiscal.AI funcionando correctamente. 🎉 