# Guía de instalación

Esta guía cubre la instalación de FICE en los tres sistemas operativos soportados. Si ya corriste el quickstart del README y todo funcionó, podés saltarte este documento.

## Prerequisites

- **Python 3.11 o superior** (`python3 --version` para verificar).
- **git** para clonar el repositorio.
- Conexión a internet la primera vez (para descargar dependencias de PyPI).

## Linux

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y python3-gi python3-gobject \
    gir1.2-webkit2-4.0 libwebkit2gtk-4.0-dev pkg-config
```

**Qué instala cada paquete:**

- `python3-gi` / `python3-gobject`: bindings de GObject para Python. Sin ellos, pywebview no puede inicializar GTK.
- `gir1.2-webkit2-4.0`: introspección GObject para WebKitGTK 4.0.
- `libwebkit2gtk-4.0-dev`: archivos de desarrollo de WebKitGTK.
- `pkg-config`: usado por el script de arranque para verificar que WebKitGTK esté presente.

### Fedora

```bash
sudo dnf install -y python3-gobject webkit2gtk4.0-devel pkgconfig
```

### Arch / Manjaro

```bash
sudo pacman -S python-gobject webkit2gtk pkgconf
```

### Verificación post-instalación

```bash
pkg-config --exists webkit2gtk-4.0 && echo "OK" || echo "Falta WebKitGTK"
python3 -c "import gi; gi.require_version('WebKit2', '4.0'); print('OK')"
```

Si ambos comandos imprimen `OK`, estás listo.

## macOS

No requiere dependencias de sistema adicionales. pywebview usa el framework WebKit que viene con el sistema.

**Requisitos:**

- macOS 10.15 (Catalina) o superior.
- Python 3.11+ (recomendamos instalarlo con [pyenv](https://github.com/pyenv/pyenv) o [Homebrew](https://brew.sh/)).
- Xcode Command Line Tools: `xcode-select --install`.

## Windows

### WebView2

WebView2 viene preinstalado en:

- Windows 11 (todas las ediciones).
- Windows 10 versión 1903 o superior con las actualizaciones al día.

Si tu equipo no lo tiene, instalalo desde:
[https://developer.microsoft.com/microsoft-edge/webview2/](https://developer.microsoft.com/microsoft-edge/webview2/)

Descargá la **Evergreen Bootstrapper** ("Standalone Installer" para entornos sin internet o el "Microsoft Edge WebView2 Runtime" desde la Microsoft Store).

### Python

Asegurate de tener Python 3.11+ y marcá la opción **"Add Python to PATH"** durante la instalación desde [python.org](https://www.python.org/downloads/).

## Pasos comunes (todos los sistemas)

Una vez instaladas las dependencias de sistema:

```bash
git clone <repo-url> fice
cd fice
chmod +x fice.sh      # Solo Linux/macOS
./fice.sh             # Linux/macOS
# o en Windows (PowerShell o Git Bash):
bash ./fice.sh
```

El script:

1. Verifica la versión de Python.
2. En Linux, chequea que WebKitGTK esté presente.
3. Crea un entorno virtual en `venv/` (la primera vez).
4. Instala las dependencias de `requirements.txt`.
5. Arranca la app en modo desktop.

## Troubleshooting

### `No module named 'gi'` al iniciar

Faltan los bindings de GObject. En Ubuntu/Debian:

```bash
sudo apt install python3-gi python3-gobject gir1.2-webkit2-4.0
```

### `GTK cannot be loaded` o `WebKit2 not found`

Misma causa que el punto anterior: WebKitGTK no está instalado o está en una versión incorrecta.

```bash
sudo apt install gir1.2-webkit2-4.0 libwebkit2gtk-4.0-dev
```

Verificá con `pkg-config --modversion webkit2gtk-4.0`.

### `ERROR: WebKitGTK not found.` (mensaje del propio `fice.sh`)

El launcher detecta automáticamente la falta de WebKitGTK y aborta con un mensaje pidiendo instalarlo. Seguí las instrucciones en pantalla o revisá las secciones de Linux de esta guía.

### Puerto 8000 ocupado

FICE escucha en `127.0.0.1:8000`. Si otro proceso lo está usando:

**Linux / macOS:**

```bash
lsof -i :8000
# Verás algo como:
# COMMAND   PID   USER   FD   TYPE  DEVICE  SIZE/OFF  NODE  NAME
# python3  12345  user   4u   IPv4  ...     0t0       TCP   127.0.0.1:8000 (LISTEN)
kill 12345
```

**Windows (PowerShell):**

```powershell
netstat -ano | findstr :8000
# El último número es el PID
taskkill /PID <pid> /F
```

### La ventana se abre en blanco

Suele pasar cuando hay un error en el servidor FastAPI. Cerrá la ventana, ejecutá `./fice.sh dev` y abrí `http://127.0.0.1:8000` en el navegador para ver el traceback completo en consola.

### En Linux la app no se ve nativa / se ve con tema blanco

Eso es normal: FICE sirve sus propios estilos desde `app/static/css/`. Si querés que use el tema del sistema, editá las hojas de estilo en esa carpeta.

### Tests fallan con `ImportError`

Asegurate de que el entorno virtual esté activo:

```bash
source venv/bin/activate   # Linux/macOS
# o
venv\Scripts\activate      # Windows
```

Y reinstalá las dependencias:

```bash
pip install -r requirements.txt
```

## Próximos pasos

Una vez que la app abre correctamente:

- Empezá creando una cuenta desde la sección **Cuentas**.
- Cargá transacciones desde la sección **Transacciones**.
- Revisá el **Dashboard** para ver tu patrimonio neto y los gráficos.

Para contribuir o reportar issues, abrí un ticket en el repositorio.
