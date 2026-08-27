"""
Gesture Flow — Unified All-in-One Master Launcher
Runs the FastAPI Backend, Web Dashboard, and Desktop CV Camera Demo simultaneously in a single command.
"""
import sys
import os
import time
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import uvicorn

# Add root directory to python path
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT_DIR)


class FrontendHandler(SimpleHTTPRequestHandler):
    """Serves the frontend directory."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(ROOT_DIR, "frontend"), **kwargs)

    def log_message(self, format, *args):
        # Suppress noisy HTTP server logs in console
        pass


def start_frontend_server(port: int = 3000):
    """Starts the static frontend HTTP server."""
    server = HTTPServer(("127.0.0.1", port), FrontendHandler)
    server.serve_forever()


def start_backend_server(host: str = "127.0.0.1", port: int = 8000):
    """Starts the FastAPI backend with MongoDB Atlas connection."""
    config = uvicorn.Config(
        "backend.main:app",
        host=host,
        port=port,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()


def run_all():
    """Launches Backend, Web Dashboard, and Desktop Camera App concurrently."""
    print("=" * 68)
    print("      [+] GESTURE FLOW - UNIFIED ALL-IN-ONE SYSTEM LAUNCHER         ")
    print("=" * 68)
    print("  [1/3] FastAPI Backend     : http://localhost:8000 (Swagger: /docs)")
    print("  [2/3] Web Management UI   : http://localhost:3000")
    print("  [3/3] Desktop CV Camera   : Initializing Real-Time MediaPipe HUD...")
    print("=" * 68)

    # 1. Start FastAPI Backend in background daemon thread
    backend_thread = threading.Thread(
        target=start_backend_server,
        args=("127.0.0.1", 8000),
        daemon=True,
        name="BackendThread"
    )
    backend_thread.start()

    # 2. Start Web Frontend Server in background daemon thread
    frontend_thread = threading.Thread(
        target=start_frontend_server,
        args=(3000,),
        daemon=True,
        name="FrontendThread"
    )
    frontend_thread.start()

    time.sleep(1.0)

    # Automatically open web dashboard in user's default browser
    try:
        webbrowser.open("http://localhost:3000")
    except Exception:
        pass

    # 3. Start Desktop Computer Vision & Camera Tracking in the main thread
    try:
        from android.main import run_desktop_interactive_mode
        run_desktop_interactive_mode(debug_latency=False, camera_idx=0)
    except (ImportError, Exception) as e:
        print(f"[Launcher] Desktop CV app skipped or running in headless mode: {e}")
        print("[Launcher] FastAPI backend (http://127.0.0.1:8000) and Web UI (http://127.0.0.1:3000) remain active.")
        print("[Launcher] Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Launcher] Shutting down...")


if __name__ == "__main__":
    is_cloud_env = bool(os.getenv("RENDER") or os.getenv("PORT") or os.getenv("ENVIRONMENT") == "production")

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ("backend", "server", "api"):
            from backend.config import settings
            port = int(os.getenv("PORT") or settings.port)
            host = "0.0.0.0" if is_cloud_env else settings.host
            print(f"[Launcher] Starting FastAPI backend on {host}:{port}...")
            uvicorn.run("backend.main:app", host=host, port=port, reload=not is_cloud_env)
        elif cmd in ("frontend", "web"):
            print("[Launcher] Starting Frontend Web Server on http://localhost:3000...")
            webbrowser.open("http://localhost:3000")
            start_frontend_server(3000)
        elif cmd in ("cv", "camera", "app"):
            from android.main import main
            main()
        elif cmd in ("all", "--all", "run"):
            run_all()
        else:
            run_all()
    else:
        # Default behavior: If deployed on Render/Cloud, run backend API on $PORT
        if is_cloud_env:
            from backend.config import settings
            port = int(os.getenv("PORT") or settings.port)
            print(f"[Launcher] Cloud/Render environment detected. Starting FastAPI backend on 0.0.0.0:{port}...")
            uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
        else:
            # Local Desktop: Run all 3 simultaneously!
            run_all()

