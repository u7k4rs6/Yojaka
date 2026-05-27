from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# Use CWD as project root — dev.py is always run from the project directory.
# Avoid Path(__file__).resolve() which can follow unexpected symlinks.
PROJECT_ROOT = Path.cwd()
FRONTEND_DIR = PROJECT_ROOT / "frontend-new"
VENV_PYTHON  = PROJECT_ROOT / ".venv" / "bin" / "python"


def stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    if not VENV_PYTHON.exists():
        print(
            f"Virtual-environment not found at {VENV_PYTHON}\n"
            "Create it first:\n"
            "  python3 -m venv .venv\n"
            "  .venv/bin/pip install -r backend/requirements.txt",
            file=sys.stderr,
        )
        return 1

    backend_cmd = [
        str(VENV_PYTHON),
        "-m", "uvicorn",
        "backend.app.main:app",
        "--reload",
        "--host", "127.0.0.1",
        "--port", "8000",
    ]

    # Static frontend served by Python's built-in HTTP server (no Node.js needed).
    frontend_cmd = [
        sys.executable,
        "-m", "http.server", "6001",
        "--directory", str(FRONTEND_DIR),
    ]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    print("Starting Yojaka — Multi-Agent Strategic Intelligence Platform...")
    print(f"Backend:  http://127.0.0.1:8000")
    print(f"Frontend: http://127.0.0.1:6001/Yojaka.html")
    print(f"Venv:     {VENV_PYTHON}")
    print("Press Ctrl+C once to stop.\n")

    backend  = subprocess.Popen(backend_cmd, cwd=str(PROJECT_ROOT), env=env)
    frontend = subprocess.Popen(frontend_cmd, cwd=str(PROJECT_ROOT), env=env)

    try:
        while True:
            bc = backend.poll()
            fc = frontend.poll()
            if bc is not None:
                print(f"Backend exited ({bc}). Stopping frontend...")
                stop_process(frontend)
                return bc
            if fc is not None:
                print(f"Frontend exited ({fc}). Stopping backend...")
                stop_process(backend)
                return fc
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        stop_process(frontend)
        stop_process(backend)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
