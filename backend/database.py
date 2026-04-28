"""
SQLite database manager for users and video generation tasks.
Uses aiosqlite for async operations.
"""

import aiosqlite
import uuid
from datetime import datetime
from backend.config import DB_PATH


async def get_db():
    """Get an async database connection."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize database tables."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)

        # Tasks table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                progress REAL NOT NULL DEFAULT 0.0,
                progress_message TEXT DEFAULT '',
                scene_duration REAL NOT NULL DEFAULT 3.0,
                num_inference_steps INTEGER NOT NULL DEFAULT 30,
                guidance_scale REAL NOT NULL DEFAULT 7.5,
                resolution INTEGER NOT NULL DEFAULT 768,
                video_path TEXT,
                thumbnail_path TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                error TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Index for faster user task lookups
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
        """)

        await db.commit()


# ──────────────────────────────────────────────
# User CRUD
# ──────────────────────────────────────────────

async def create_user(username: str, email: str, hashed_password: str) -> dict:
    """Create a new user and return user dict."""
    user_id = str(uuid.uuid4())
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO users (id, username, email, hashed_password) VALUES (?, ?, ?, ?)",
            (user_id, username, email, hashed_password)
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row)


async def get_user_by_username(username: str) -> dict | None:
    """Find a user by username."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_email(email: str) -> dict | None:
    """Find a user by email."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_id(user_id: str) -> dict | None:
    """Find a user by ID."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# ──────────────────────────────────────────────
# Task CRUD
# ──────────────────────────────────────────────

async def create_task(
    user_id: str,
    prompt: str,
    scene_duration: float,
    num_inference_steps: int,
    guidance_scale: float,
    resolution: int
) -> dict:
    """Create a new generation task."""
    task_id = str(uuid.uuid4())
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """INSERT INTO tasks (id, user_id, prompt, scene_duration,
               num_inference_steps, guidance_scale, resolution)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task_id, user_id, prompt, scene_duration,
             num_inference_steps, guidance_scale, resolution)
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row)


async def get_task(task_id: str) -> dict | None:
    """Get a task by ID."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_tasks(user_id: str, limit: int = 50) -> list[dict]:
    """Get all tasks for a user, newest first."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_task_progress(
    task_id: str,
    progress: float,
    message: str = "",
    status: str = "processing"
):
    """Update task progress."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """UPDATE tasks SET progress = ?, progress_message = ?, status = ?
               WHERE id = ?""",
            (progress, message, status, task_id)
        )
        await db.commit()


async def complete_task(task_id: str, video_path: str, thumbnail_path: str = None):
    """Mark a task as completed."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """UPDATE tasks SET status = 'completed', progress = 100.0,
               progress_message = 'Video ready!', video_path = ?,
               thumbnail_path = ?, completed_at = ?
               WHERE id = ?""",
            (video_path, thumbnail_path, datetime.utcnow().isoformat(), task_id)
        )
        await db.commit()


async def fail_task(task_id: str, error: str):
    """Mark a task as failed."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """UPDATE tasks SET status = 'failed', progress_message = ?,
               error = ?, completed_at = ?
               WHERE id = ?""",
            (f"Failed: {error}", error, datetime.utcnow().isoformat(), task_id)
        )
        await db.commit()


async def delete_task(task_id: str):
    """Delete a task record."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()
