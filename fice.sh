#!/usr/bin/env bash
set -euo pipefail

# FICE — Personal Finance Tracker Launcher
# Usage: ./fice.sh [dev|test]
#   (no args)  Launch the native desktop window.
#   dev         Start in dev mode (browser at http://127.0.0.1:8000).
#   test        Run the test suite.
#
# System dependencies on Linux (Ubuntu/Debian):
#   sudo apt install python3-gi gir1.2-webkit2-4.0 libwebkit2gtk-4.0-dev pkg-config
# See docs/setup.md for other OSes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---- Python version check ----
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
    || { echo "ERROR: Python 3.11+ is required."; exit 1; }

# ---- System deps check (Linux) ----
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! pkg-config --exists webkit2gtk-4.0 2>/dev/null && \
       ! pkg-config --exists webkit2gtk-4.1 2>/dev/null; then
        echo "ERROR: WebKitGTK not found."
        echo "Install it: sudo apt install python3-gi gir1.2-webkit2-4.0 libwebkit2gtk-4.0-dev pkg-config"
        echo "See docs/setup.md for full instructions."
        exit 1
    fi
fi

# ---- Virtual environment ----
if [ ! -d "venv" ]; then
    python3 -m venv --system-site-packages venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# ---- Dispatch ----
case "${1:-run}" in
    dev)
        echo "Starting in dev mode → http://127.0.0.1:8000"
        exec uvicorn app:create_app --reload --factory
        ;;
    test)
        exec python -m pytest tests/ -v
        ;;
    run|*)
        exec python main.py
        ;;
esac
