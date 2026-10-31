"""
AdeptLearn Backend Entrypoint Script
Run this script to initialize and start the FastAPI backend server:
    python run.py
"""

import sys
import os
import uvicorn
from pathlib import Path


def main():
    # Ensure current directory is in Python path
    base_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(base_dir))

    # Server configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    print("=" * 60)
    print("🚀 Starting AdeptLearn Adaptive Exam-Prep Backend")
    print(f"📍 Server Address : http://{host}:{port}")
    print(f"📖 Interactive Docs : http://localhost:{port}/docs")
    print(f"📚 ReDoc Docs       : http://localhost:{port}/redoc")
    print(f"💓 Liveness Probe   : http://localhost:{port}/health/live")
    print(f"📊 System Status    : http://localhost:{port}/api/v1/system/status")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
