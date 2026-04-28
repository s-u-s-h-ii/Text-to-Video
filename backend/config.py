"""
Centralized configuration for the Text-to-Video Studio.
All settings can be overridden via environment variables or a .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ──────────────────────────────────────────────
# Server
# ──────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
TASKS_DIR = DATA_DIR / "tasks"
DB_PATH = DATA_DIR / "database.db"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
TASKS_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────
# AI Model
# ──────────────────────────────────────────────
MODEL_ID = os.getenv("MODEL_ID", "playgroundai/playground-v2-1024px-aesthetic")
DEVICE = os.getenv("DEVICE", "cuda")  # "cuda" or "cpu"
TORCH_DTYPE = os.getenv("TORCH_DTYPE", "float16")  # "float16" or "float32"

# ──────────────────────────────────────────────
# Generation Defaults
# ──────────────────────────────────────────────
DEFAULT_SCENE_DURATION = float(os.getenv("DEFAULT_SCENE_DURATION", "3.0"))
DEFAULT_NUM_INFERENCE_STEPS = int(os.getenv("DEFAULT_NUM_INFERENCE_STEPS", "30"))
DEFAULT_GUIDANCE_SCALE = float(os.getenv("DEFAULT_GUIDANCE_SCALE", "7.5"))
DEFAULT_RESOLUTION = int(os.getenv("DEFAULT_RESOLUTION", "768"))
MAX_SENTENCES = int(os.getenv("MAX_SENTENCES", "20"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "24"))

# ──────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "text-to-video-studio-secret-key-change-me-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
ALGORITHM = "HS256"
