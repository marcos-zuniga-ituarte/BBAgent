# Clientes de herramientas de BBAgent

Este README se incluye en `clients.zip`, disponible en la web desde **Configuración → Download clients**. El paquete permite conectar una terminal o un escritorio a tu servidor BBAgent. No necesitas instalar el backend en el equipo que quieres controlar.

Descomprime el ZIP completo, conserva `libraries/` y ejecuta los comandos desde la carpeta `clients/`. Necesitas Python 3.12 o 3.13 y un usuario de BBAgent ya creado en el servidor.

Son clientes distintos: `reverse_bbagent_computer_use.py` habilita pantalla, ratón y teclado; `reverse_bbagent_terminal.py` habilita comandos de terminal. Arrancar el primero no conecta el segundo. Si necesitas ambos, mantenlos abiertos en terminales independientes.

## Windows: control gráfico

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe reverse_bbagent_computer_use.py --url http://localhost:8000
```

El cliente de terminal utiliza Bash/PTY y no funciona directamente con Python nativo de Windows. Para terminal, utiliza Linux/macOS o un entorno Python propio dentro de WSL.

## Linux/macOS: solo terminal

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-terminal.txt
.venv/bin/python reverse_bbagent_terminal.py --url http://localhost:8000
```

## Linux/macOS: control gráfico o ambos clientes

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reverse_bbagent_computer_use.py --url http://localhost:8000
```

Para conectar también la terminal, abre otra terminal en esta misma carpeta y ejecuta:

```bash
.venv/bin/python reverse_bbagent_terminal.py --url http://localhost:8000
```

El control gráfico necesita un escritorio interactivo compatible y puede requerir permisos de captura de pantalla y accesibilidad. En algunos sistemas Linux puede ser necesario instalar componentes de Tk o captura de pantalla mediante el gestor de paquetes del sistema; pip solo instala las dependencias Python. En WSL, el cliente de terminal controla el entorno de WSL.

## Windows + WSL: terminal con backend en Windows

El cliente de terminal se ejecuta con Python de Linux dentro de WSL y controla la terminal de WSL. El cliente gráfico se ejecuta con Python de Windows para controlar el escritorio de Windows.

### 1. Preparar el cliente en WSL

Desde la carpeta `clients/` extraída, abre una terminal WSL y crea un entorno propio. Si la carpeta se comparte con Windows, utiliza `.venv-wsl` para no sobrescribir su `.venv`: los entornos de ambos sistemas no son intercambiables.

```bash
python3 -m venv .venv-wsl
.venv-wsl/bin/python -m pip install -r requirements-terminal.txt
```

### 2. Permitir la conexión al backend

En el modo NAT de WSL 2, `localhost` dentro de WSL no apunta al servidor de Windows. Si el backend escucha solo en `127.0.0.1`, el cliente puede recibir `Connection refused` antes de autenticar al usuario. Con la red en modo mirrored, se puede utilizar `localhost`. Consulta la [documentación de red de WSL](https://learn.microsoft.com/en-us/windows/wsl/networking).

Si administras el backend en Windows, detén su proceso con `Ctrl+C` y, desde su carpeta `backend/` y su entorno virtual de Windows, arráncalo para aceptar conexiones desde WSL:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir src --host 0.0.0.0 --port 8000 --reload
```

Este comando corresponde a la instalación del servidor, no a la carpeta del ZIP. Escucha en todas las interfaces: utilízalo en un entorno de confianza, mantén el firewall activo y evita exponer la API a Internet. No necesitas cambiar CORS para la conexión de un cliente Python.

### 3. Conectar el cliente a Windows

En WSL, desde `clients/`, obtén la dirección de Windows y arranca el cliente:

```bash
BBAGENT_WINDOWS_HOST=$(ip route show default | awk '{print $3; exit}')
.venv-wsl/bin/python reverse_bbagent_terminal.py --url "http://${BBAGENT_WINDOWS_HOST}:8000"
```

La dirección puede cambiar al reiniciar WSL; vuelve a obtenerla en cada sesión. Introduce el mismo usuario de BBAgent que utilizas en la web y deja el cliente abierto. Si tienes habilitada la red mirrored, puedes utilizar `--url http://localhost:8000`.

Si sigue apareciendo `Connection refused` o un timeout, comprueba que el backend está activo, que la URL es correcta y que el firewall permite la conexión desde WSL. Es un problema de conectividad, anterior a la comprobación de la contraseña.

## Conexión y credenciales

- Sustituye `http://localhost:8000` por la URL de tu backend si está en otro equipo. `localhost` apunta al ordenador donde ejecutas el cliente.
- También puedes configurar `BBAGENT_API_URL` en la terminal. `--url` tiene prioridad; sin ninguna opción se usa `http://localhost:8000`.
- Cuando aparezcan `Login:` y `Contraseña:`, introduce las credenciales de **BBAgent**, las mismas de la web. La contraseña no muestra caracteres mientras la escribes.
- No se necesita la clave API de OpenAI en estos clientes. Esa clave pertenece al servidor.
- Mantén cada cliente abierto mientras utilizas su herramienta. Para desconectarlo, pulsa `Ctrl+C`.

El cliente ejecuta acciones con los permisos de tu cuenta del sistema. Utiliza HTTPS si te conectas a una API fuera de tu entorno local y no escribas credenciales dentro de los scripts.

## Archivos de dependencias

- `requirements.txt`: instala lo necesario para ambos clientes, incluido el control gráfico.
- `requirements-terminal.txt`: instala únicamente lo necesario para terminal, sin dependencias de escritorio.

El ZIP incluye código Python, estos archivos de dependencias y esta guía. No incluye `.env`, credenciales, entornos virtuales ni cachés.
