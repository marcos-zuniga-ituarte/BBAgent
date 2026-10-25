# Backend de BBAgent

API en Python y FastAPI para autenticación, conversaciones, archivos y ejecución del agente. Utiliza SQLite para persistencia y OpenAI para generación de respuestas, transcripción y memoria. La interfaz web se ejecuta por separado: consulta el [README global](../README.md).

## Requisitos

- Python 3.12 o 3.13.
- Una clave de OpenAI vigente y acceso a los modelos configurados para utilizar el agente.
- Docker Desktop o Docker Engine si prefieres ejecutar con contenedores.

Todos los comandos siguientes se ejecutan desde `backend/`, salvo donde se indique lo contrario. Conserva `data/prompts/` y `data/tools/`: son recursos necesarios para la aplicación.

## 1. Configurar el entorno

Copia [.env.example](.env.example) a `.env` **solo si todavía no tienes un `.env` configurado**.

Windows, desde la raíz del proyecto:

```powershell
cd backend
Copy-Item .env.example .env
```

Linux/macOS, desde la raíz:

```bash
cd backend
cp .env.example .env
```

Abre `.env` en tu editor y sustituye el marcador por tu clave real, sin comillas ni espacios alrededor del signo igual:

```dotenv
OPENAI_API_KEY=tu_clave_de_openai
```

No uses literalmente `tu_clave_de_openai`. No publiques `.env`: contiene configuración privada y está excluido por `.gitignore`.

El ejemplo contiene todas las variables utilizadas y comentarios sobre cómo configurarlas:

| Variable | Qué configura |
| --- | --- |
| `OPENAI_API_KEY` | Clave privada para las llamadas a OpenAI. |
| `DATABASE_PATH` | Archivo SQLite; por defecto `data/bd/local.db`. No es una URL de conexión. |
| `CORS_ALLOWED_ORIGINS` | Orígenes web permitidos, separados por comas. Por defecto, los de Vite y preview locales. |
| `OPENAI_AGENT_MODEL` | Modelo principal del agente. |
| `OPENAI_TRANSCRIPTION_MODEL` | Modelo para transcribir audio. |
| `OPENAI_MEMORY_MODEL` | Modelo para actualizar y reconstruir memoria. |
| `CONTEXT_HISTORY_RUNS` | Turnos históricos conservados en el contexto; entero mayor o igual que cero. |
| `CHAT_TITLE_MAX_LENGTH` | Máximo de caracteres del título inicial; entero positivo. |
| `TERMINAL_IDLE_TIMEOUT_SECONDS` | Tiempo sin salida de la terminal, en segundos; número positivo. |
| `AGENT_PROMPT` | Archivo de instrucciones del agente. |
| `MEMORY_PROMPT` | Archivo para actualizar memoria. |
| `MEMORY_PROMPT_FULL_REBUILD` | Archivo para reconstruir memoria. |

Los nombres de prompts corresponden a archivos de `data/prompts/`, sin extensión `.txt`. Los modelos deben estar disponibles para tu cuenta. Las variables del sistema tienen prioridad sobre los valores de `.env`. Si tu archivo local todavía no incluye `CORS_ALLOWED_ORIGINS`, se aplican los orígenes locales del ejemplo. Para otra web, añade su origen completo; no uses `*`.

La base SQLite y su directorio se crean al configurar el acceso a datos. Cambiar `DATABASE_PATH` selecciona otra base: no migra ni elimina la anterior. Las rutas relativas se resuelven desde el directorio de ejecución, por eso debes trabajar desde `backend/`.

## 2. Instalar las dependencias

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
```

Se utiliza directamente el Python del entorno virtual; no es necesario activar scripts ni cambiar la política de ejecución de PowerShell.

### Linux/macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"
```

Vuelve a establecer `PYTHONPATH` si abres otra terminal para ejecutar la API, la CLI o las pruebas.

## 3. Crear un usuario

Antes de iniciar sesión en la web, crea un usuario con la CLI. Te pedirá el login, la contraseña y su confirmación.

Windows:

```powershell
.\.venv\Scripts\python.exe -m app.cli create-user
```

Linux/macOS:

```bash
.venv/bin/python -m app.cli create-user
```

La CLI y la API deben usar el mismo `.env` y la misma base de datos. Crear usuarios no requiere llamadas a OpenAI.

## 4. Arrancar la API

Windows:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Linux/macOS:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API: http://localhost:8000
- Documentación de endpoints: http://localhost:8000/docs
- Esquema OpenAPI: http://localhost:8000/openapi.json

Mantén esta terminal abierta. Para detener la API, pulsa `Ctrl+C`. `--reload` es para desarrollo: reinicia el servidor al cambiar el código. La página `/docs` muestra los endpoints, pero esta aplicación deshabilita su ejecución interactiva desde Swagger.

Para usar la interfaz, arranca también el [frontend](../frontend/README.md) en otra terminal e inicia sesión con el usuario creado. Su URL de API local debe ser `http://localhost:8000`.

El arranque anterior escucha únicamente en el equipo local. Si ejecutas el cliente de terminal en WSL y el backend en Windows, consulta la [conexión Windows + WSL](clients/README.md#windows--wsl-terminal-con-backend-en-windows) del README incluido en el ZIP. En modo NAT, el cliente necesita la dirección de Windows y una API que acepte conexiones desde esa interfaz.

## Ejecución con Docker

Configura primero `backend/.env` siguiendo el paso 1.

### Solo backend

Desde `backend/`:

```bash
docker compose up --build
```

En otra terminal, también desde `backend/`, crea un usuario:

```bash
docker compose exec bbagent python -m app.cli create-user
```

Este Compose monta el código local y ejecuta la API con recarga de desarrollo. Utiliza `DATABASE_PATH` de `.env`.

Para ejecutar backend y frontend juntos, utiliza el Compose de la raíz siguiendo el [README global](../README.md#ejecución-con-docker). Los puertos de ambos Compose se publican solo en el equipo local.

Para detener el backend independiente, ejecuta `docker compose down` desde `backend/`. La base SQLite del equipo se conserva.

## Descarga de clientes de herramientas

El endpoint autenticado `GET /tool-client/download` devuelve `clients.zip`. La interfaz lo ofrece desde **Configuración → Download clients**.

El paquete contiene los clientes de terminal y control gráfico, sus archivos `requirements` y un `README.md` con las instrucciones de instalación y conexión para cada sistema operativo. Sigue esa guía después de descargarlo. Los clientes se ejecutan por separado del servidor.

## Pruebas

Desde `backend/`, con las dependencias instaladas:

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest src/test
```

Linux/macOS:

```bash
.venv/bin/python -m pytest src/test
```

Las pruebas utilizan SQLite temporal y una clave ficticia, sin llamadas a OpenAI ni lectura de tu base real. Comprueban acceso a datos, autenticación y revocación de sesiones, aislamiento entre usuarios, CORS, descargas de archivos y exportación de clientes.

## Problemas habituales

| Problema | Qué revisar |
| --- | --- |
| `No module named app` | Ejecuta desde `backend/` y establece `PYTHONPATH` como indica el paso 2. |
| Error de autenticación de OpenAI | Sustituye el marcador por una clave vigente en `.env`; revisa también las variables del sistema. |
| Modelo no disponible | Ajusta los modelos de `.env` a los que permite tu cuenta. |
| Variable ausente o error al convertir un número | Compara tu `.env` con `.env.example` y respeta los formatos documentados. |
| Prompt no encontrado | Comprueba que existe `data/prompts/<nombre>.txt` y ejecuta desde `backend/`. |
| No puedes iniciar sesión | Crea el usuario con la CLI y verifica que utiliza la misma base que la API. |
| El puerto 8000 está ocupado | Detén la otra instancia o cambia el puerto y la URL configurada en el frontend y los clientes. |
