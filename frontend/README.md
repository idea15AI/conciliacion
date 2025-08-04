# Frontend - Sistema RAG

Frontend en Next.js con TypeScript y Tailwind CSS para el Sistema RAG Multiempresa.

## Configuración

1. Instalar dependencias:
```bash
npm install
```

2. Crear archivo `.env.local` en la raíz del proyecto frontend:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. Ejecutar en modo desarrollo:
```bash
npm run dev
```

## Estructura del Proyecto

### Páginas principales:

- **`/`** - Página principal que redirige automáticamente
- **`/login`** - Formulario de inicio de sesión
- **`/dashboard`** - Dashboard principal (protegido)
- **`/documentos/subir`** - Subir documentos PDF (protegido)
- **`/ia/chat`** - Chat con IA para hacer preguntas (protegido)

### Componentes:

- **`Layout`** - Layout base con navbar y logout
- **`ProtectedRoute`** - Componente para proteger rutas que requieren autenticación

### Hooks:

- **`useAuth`** - Hook personalizado para manejar autenticación

### API:

- **`lib/api.ts`** - Configuración centralizada de API con axios
- Interceptores automáticos para JWT
- Manejo de errores de autenticación

## Funcionalidades

### Autenticación
- Login con email/contraseña
- JWT almacenado en localStorage
- Redirección automática según estado de autenticación
- Logout con limpieza de token

### Subida de Documentos
- Selector de archivos PDF (máximo 10MB)
- Selector múltiple de categorías
- Validación de archivos
- Feedback de éxito/error

### Chat con IA
- Interfaz de chat para hacer preguntas
- Procesamiento en tiempo real
- Mostrar respuesta de IA
- Lista de fuentes consultadas con relevancia

### Diseño
- Diseño responsive con Tailwind CSS
- Interfaz limpia y moderna
- Estados de carga
- Mensajes de error/éxito
- Iconos SVG integrados

## Tecnologías

- **Next.js 15** - Framework React
- **TypeScript** - Tipado estático
- **Tailwind CSS** - Estilos
- **Axios** - Cliente HTTP
- **React Hooks** - Manejo de estado

## Desarrollo

El frontend se conecta automáticamente al backend FastAPI en `http://localhost:8000`.

Asegúrate de que el backend esté ejecutándose antes de usar el frontend.

### Comandos útiles:

```bash
# Desarrollo
npm run dev

# Build para producción
npm run build

# Ejecutar build de producción
npm start

# Linting
npm run lint
```

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
