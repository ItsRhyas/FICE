"""Desktop entry point for FICE.

Starts a FastAPI server in a daemon thread and opens a native pywebview window.
Closing the window terminates the process and the daemon thread.

Development (browser): `uvicorn app:create_app --reload`
Production (desktop):  `python main.py`
"""

import threading

import uvicorn
import webview

from app import create_app

app = create_app()


def run_server() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    webview.create_window(
        "FICE",
        "http://127.0.0.1:8000",
        width=1200,
        height=800,
    )
    webview.start()
    # webview.start() blocks; closing the window exits the process, which also
    # terminates the daemon server thread and releases the bound port.
