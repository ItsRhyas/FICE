# FICE — Personal Finance Tracker

> Rastreador de finanzas personales que corre como aplicación de escritorio nativa. Datos locales, sin nube, sin cuentas, sin telemetría.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)

## Overview

FICE es una aplicación de escritorio para llevar el control de tus finanzas personales. Maneja cuentas y transacciones, calcula patrimonio neto automáticamente y muestra gráficos de tendencia y distribución sin salir de la app.

Toda la información se guarda en un archivo SQLite local. La interfaz se sirve desde FastAPI y se abre en una ventana nativa gracias a pywebview, por lo que la experiencia es la de una app de escritorio real (sin navegador, sin puerto expuesto a la red).

## Features

- **Cuentas**: alta, baja, modificación y listado de cuentas (efectivo, banco, tarjeta, brokerage, etc.).
- **Transacciones**: CRUD completo con fecha, descripción, monto, cuenta y tipo (ingreso / egreso / transferencia).
- **Dashboard**: vista general con patrimonio neto actual, totales por cuenta y resumen de movimientos.
- **Gráficos de tendencia**: evolución del patrimonio en el tiempo (Chart.js).
- **Distribución por cuenta**: gráfico de torta con la composición de tu dinero.
- **Single-user, local-first**: sin login, sin servidor remoto. Tus datos no salen de tu máquina.
- **Servidor embebido**: FastAPI escucha en `127.0.0.1:8000` solo dentro de la ventana nativa.
- **Arquitectura por capas**: routes → services → models → db (factory pattern de FastAPI).

## Quickstart

### 1. Clonar el repositorio

```bash
git clone <repo-url> fice
cd fice
```

### 2. Instalar dependencias de sistema

#### Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y python3-gi python3-gobject \
    gir1.2-webkit2-4.0 libwebkit2gtk-4.0-dev pkg-config
```

#### Linux (Fedora)

```bash
sudo dnf install -y python3-gobject webkit2gtk4.0-devel pkgconfig
```

#### macOS

No requiere dependencias de sistema adicionales. pywebview usa el WebKit nativo del sistema.

#### Windows

WebView2 viene preinstalado en Windows 10 y Windows 11. Si usás una versión anterior, instalalo desde [la página oficial de Microsoft Edge WebView2](https://developer.microsoft.com/microsoft-edge/webview2/).

Para instrucciones detalladas por sistema operativo, consultá [`docs/setup.md`](docs/setup.md).

### 3. Ejecutar

**Linux / macOS:**

```bash
chmod +x fice.sh
./fice.sh
```

**Windows:**

```cmd
fice.bat
```

El script se encarga de crear el entorno virtual, instalar las dependencias de Python y abrir la ventana nativa de la app. La primera vez puede tardar unos minutos mientras se descargan los paquetes.

## Usage

Ambos launchers aceptan los mismos modos:

| Linux / macOS     | Windows        | Qué hace                                                                 |
|--------------------|----------------|--------------------------------------------------------------------------|
| `./fice.sh`       | `fice.bat`     | Modo normal: abre la ventana nativa de la app.                           |
| `./fice.sh dev`   | `fice.bat dev` | Modo desarrollo: levanta el servidor en `http://127.0.0.1:8000` con autoreload. |
| `./fice.sh test`  | `fice.bat test`| Corre la suite de tests con pytest.                                      |

## Project Structure

```
FICE/
├── app/                    # Código de la aplicación
│   ├── routes/             # Endpoints de FastAPI
│   │   ├── accounts.py
│   │   ├── dashboard.py
│   │   └── transactions.py
│   ├── services.py         # Lógica de negocio
│   ├── models.py           # Modelos SQLModel
│   ├── db.py               # Configuración de SQLite (WAL mode)
│   ├── templating.py       # Configuración de Jinja2
│   ├── templates/          # Plantillas Jinja2 (base, dashboard, accounts, transactions, partials)
│   └── static/             # CSS y JS estáticos
├── tests/                  # Tests con pytest + httpx
│   ├── test_accounts.py
│   ├── test_dashboard.py
│   ├── test_models.py
│   └── test_transactions.py
├── data/                   # Base de datos SQLite (generada al primer arranque)
├── fice.sh                 # Launcher (Linux / macOS)
├── fice.bat                # Launcher (Windows)
├── main.py                 # Entry point desktop (arranca FastAPI + pywebview)
├── requirements.txt        # Dependencias de Python
└── openspec/               # Specs y cambios bajo el flujo OpenSpec
```

## Stack

| Capa        | Tecnología                                      |
|-------------|-------------------------------------------------|
| Backend     | FastAPI                                         |
| ORM         | SQLModel (sobre SQLAlchemy 2.0)                 |
| Base de datos | SQLite con WAL mode                           |
| Templates   | Jinja2                                          |
| Interactividad | HTMX (cargado desde CDN)                     |
| Gráficos    | Chart.js (cargado desde CDN)                    |
| Desktop     | pywebview (WebKitGTK en Linux, WebView2 en Windows, WebKit en macOS) |
| Server      | Uvicorn                                         |
| Tests       | pytest + httpx                                  |

## Development

### Modo desarrollo (con hot-reload)

```bash
./fice.sh dev
```

Levanta Uvicorn con `--reload` en `http://127.0.0.1:8000`. Abrí esa URL en el navegador para trabajar sin la ventana nativa. Los cambios en `app/` se recargan automáticamente.

### Tests

```bash
./fice.sh test
```

Corre los 72 tests con pytest de forma verbosa. Los tests usan una base SQLite en memoria, así que son rápidos y no pisan tus datos.

### Flujo de trabajo con specs

El proyecto usa [OpenSpec](https://github.com/Fission-AI/OpenSpec) para gestionar cambios. Mirá la carpeta `openspec/` y el archivo `openspec/AGENTS.md` para entender el flujo `propose → spec → design → tasks → apply → verify → archive`.

## License

MIT. El archivo `LICENSE` se incluirá en una próxima iteración; por ahora la intención del proyecto es distribuirse bajo términos MIT.
