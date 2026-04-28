"""
Text-to-Video Studio -- Entry Point
Run this file to start the entire application.
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import uvicorn
from backend.config import HOST, PORT, DEBUG

if __name__ == "__main__":
    print("")
    print("  Text-to-Video Studio")
    print(f"  Server: http://localhost:{PORT}")
    print(f"  API Docs: http://localhost:{PORT}/docs")
    print(f"  Debug: {DEBUG}")
    print("")

    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info",
    )
