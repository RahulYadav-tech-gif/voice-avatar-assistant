# main.py
import threading
import uvicorn
from livekit.agents import WorkerOptions, cli

from tavus_agent import entrypoint
from api import app

def run_fastapi():
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

def run_worker():
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    threading.Thread(target=run_fastapi, daemon=True).start()
    run_worker()
