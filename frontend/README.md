# Frontend de BBAgent

Interfaz React/Vite para iniciar sesión, gestionar conversaciones y utilizar el agente mediante HTTP y streaming SSE. Necesita el [backend](../backend/README.md) en funcionamiento; la clave de OpenAI se configura únicamente en el backend.

Puedes ver la conversación, la confirmación de herramientas y la vista compacta en la [galería del proyecto](../README.md#interfaz).

## Requisitos

- Node.js 22.12 o posterior de la rama 22, o Node.js 24 o posterior.
- npm, incluido con Node.js.
- API del backend accesible y un usuario creado con su CLI.

Todos los comandos siguientes se ejecutan desde `frontend/`, salvo donde se indique lo contrario. Esta carpeta usa Node.js: no necesita un entorno virtual de Python ni `requirements.txt`.

## 1. Configurar la conexión

Windows, desde la raíz del proyecto:

```powershell
cd frontend
Copy-Item .env.example .env.local
```

Linux/macOS, desde la raíz:

```bash
cd frontend
cp .env.example .env.local
```

Copia el ejemplo solo si todavía no tienes `.env.local` configurado. Para uso local, deja este valor:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Es la única variable de entorno que consume actualmente la web. Debe ser una URL absoluta HTTP o HTTPS, accesible desde el navegador, sin credenciales, parámetros ni fragmentos. Puede incluir un prefijo de ruta si tu API lo necesita. Las barras finales se normalizan automáticamente.

Si no defines la variable, se usa `http://localhost:8000`. Reinicia Vite tras cambiar `.env.local`. Las variables `VITE_*` son públicas y se incorporan al JavaScript durante la compilación: nunca introduzcas claves API, contraseñas o tokens en ellas. `.env.local` queda excluido de Git y del contexto de Docker.

## 2. Instalar dependencias

Windows (PowerShell):

```powershell
npm.cmd ci
```

Linux/macOS:

```bash
npm ci
```

`npm ci` instala las versiones registradas en `package-lock.json`. Conserva este archivo para que otras personas puedan reproducir la instalación. En PowerShell se usa `npm.cmd` para evitar restricciones de ejecución de scripts.

## 3. Arrancar la interfaz

Deja el backend funcionando en su terminal y abre otra para el frontend.

Windows:

```powershell
npm.cmd run dev
```

Linux/macOS:

```bash
npm run dev
```

Abre http://localhost:5173 e inicia sesión con el usuario creado en el backend. Vite escucha solo en el equipo local. El puerto está fijado: si está ocupado, el arranque falla en lugar de cambiar silenciosamente de puerto.

Mantén la terminal abierta. Para detener Vite, pulsa `Ctrl+C`. Los cambios de código se reflejan durante el desarrollo sin recompilar manualmente.

## 4. Utilizar la aplicación

1. Inicia sesión con el usuario creado en el backend.
2. Crea una conversación con **Nuevo chat** y escribe un mensaje. La respuesta se muestra por streaming.
3. Desde **Configuración**, puedes ajustar las preferencias y descargar los clientes para habilitar las herramientas de terminal y control gráfico.

### Descargar herramientas

Abre **Configuración → Download clients**. Se descargará `clients.zip`, que incluye los scripts, sus dependencias y un `README.md` con los pasos de instalación y conexión. Descomprime el paquete y sigue esa guía en el equipo que quieras controlar.

La web y el backend no inician esos clientes automáticamente. Puedes conversar sin conectarlos; las acciones de terminal y escritorio requieren el cliente correspondiente.

Enviar mensajes al agente utiliza la clave configurada en el backend y puede generar consumo de API.

## Pruebas y compilación

Windows:

```powershell
npm.cmd test
npm.cmd run lint -- --max-warnings 0
npm.cmd run build
npm.cmd run preview
```

Linux/macOS:

```bash
npm test
npm run lint -- --max-warnings 0
npm run build
npm run preview
```

- `test`: valida la URL de configuración y el filtrado de HTML peligroso en los mensajes.
- `lint`: revisa el código y los hooks de React.
- `build`: genera los archivos estáticos en `dist/`.
- `preview`: sirve la compilación en http://localhost:4173 para comprobarla localmente; requiere ejecutar `build` antes.

Puedes compilar sin arrancar el backend; para utilizar la aplicación necesitas una API accesible. Cambiar variables después de generar `dist/` no modifica esa compilación: hay que volver a ejecutar `build`.

## Docker

### Solo frontend

Desde `frontend/`:

```bash
docker compose up --build
```

La interfaz estará en http://localhost:5173, servida por Nginx. Debes iniciar el backend por separado. Este modo sirve una compilación estática y no tiene la recarga de desarrollo de Vite.

Para ejecutar backend y frontend juntos, consulta la [ejecución con Docker del README global](../README.md#ejecución-con-docker).

Para detener el frontend independiente, ejecuta `docker compose down` desde `frontend/`.

### Otra URL de API en Docker

Los archivos `.env` no se copian a la imagen. El Dockerfile recibe la URL pública mediante un argumento de compilación. Desde la raíz:

```bash
docker compose build --build-arg VITE_API_BASE_URL=https://api.example.com frontend
docker compose up
```

Sustituye el dominio de ejemplo por la dirección real. En Docker, `localhost` corresponde al equipo donde se abre el navegador; no es el nombre del contenedor del backend. Nginx conserva el fallback de rutas para poder recargar páginas como `/chat`.

## Sesión y contenido

El token de sesión se obtiene al iniciar sesión y se guarda en `localStorage`; no forma parte del repositorio ni de `.env.local`. No compartas el almacenamiento del navegador ni pegues tokens en archivos de configuración. La autorización de los endpoints corresponde al backend.

Los mensajes Markdown que incluyen HTML se sanitizan antes de mostrarse, eliminando etiquetas, atributos y protocolos peligrosos. Esto permite conservar formato compatible sin confiar en HTML arbitrario.

## Problemas habituales

| Problema | Qué revisar |
| --- | --- |
| `npm` no se encuentra | Instala una versión compatible de Node.js y abre otra terminal. |
| PowerShell bloquea `npm.ps1` | Utiliza `npm.cmd`, como en los ejemplos. |
| Puerto 5173 ocupado | Detén la otra instancia de Vite antes de arrancar. |
| Error de URL al abrir la web | Revisa `VITE_API_BASE_URL` en `.env.local` y reinicia Vite. |
| No conecta con la API | Comprueba que el backend sigue funcionando y que su dirección coincide con la configuración. |
| No puedes iniciar sesión | Verifica el usuario y que el backend utiliza la base donde lo creaste. |
| La web sigue usando la URL anterior | Reinicia Vite o vuelve a compilar si utilizas `dist/` o Docker. |
| Error de CORS o contenido mixto | Revisa los orígenes permitidos del backend; una web HTTPS necesita una API HTTPS. |
