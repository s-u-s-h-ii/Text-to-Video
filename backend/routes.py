"""
API route definitions for the Text-to-Video Studio.
"""

import shutil
import torch
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from jose import JWTError, jwt

from backend.auth import get_current_user, register_user, authenticate_user, create_access_token
from backend.config import MODEL_ID, TASKS_DIR, SECRET_KEY, ALGORITHM
from backend.models import (
    RegisterRequest, LoginRequest, AuthResponse, UserInfo,
    GenerationRequest, GenerationResponse,
    TaskStatusResponse, TaskListItem,
    HealthResponse, MessageResponse,
)
from backend import database
from backend.pipeline import ModelManager, start_generation

router = APIRouter(prefix="/api")


async def get_user_from_token_param(token: str = Query(...)) -> dict:
    """Extract user from a ?token= query parameter. Used for media endpoints
    where browsers can't send Authorization headers (img/video tags)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=403, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")
    user = await database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=403, detail="User not found")
    return user


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Server health check with GPU and model status."""
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else None
    model_mgr = ModelManager.get_instance()

    return HealthResponse(
        status="healthy",
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        model_loaded=model_mgr.is_loaded,
        model_id=MODEL_ID,
    )


# ──────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────

@router.post("/auth/register", response_model=AuthResponse, tags=["Auth"])
async def register(req: RegisterRequest):
    """Register a new user account."""
    user = await register_user(req.username, req.email, req.password)
    token = create_access_token(data={"sub": user["id"]})
    return AuthResponse(
        access_token=token,
        user=UserInfo(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"],
        )
    )


@router.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(req: LoginRequest):
    """Login with username and password."""
    user = await authenticate_user(req.username, req.password)
    token = create_access_token(data={"sub": user["id"]})
    return AuthResponse(
        access_token=token,
        user=UserInfo(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"],
        )
    )


@router.get("/auth/me", response_model=UserInfo, tags=["Auth"])
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserInfo(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"],
    )


# ──────────────────────────────────────────────
# Video Generation
# ──────────────────────────────────────────────

@router.post("/generate", response_model=GenerationResponse,
             status_code=status.HTTP_202_ACCEPTED, tags=["Generation"])
async def submit_generation(req: GenerationRequest, user: dict = Depends(get_current_user)):
    """Submit a text prompt for video generation."""
    # Validate resolution
    if req.resolution not in [512, 768, 1024]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolution must be 512, 768, or 1024"
        )

    # Create task in database
    task = await database.create_task(
        user_id=user["id"],
        prompt=req.prompt,
        scene_duration=req.scene_duration,
        num_inference_steps=req.num_inference_steps,
        guidance_scale=req.guidance_scale,
        resolution=req.resolution,
    )

    # Start background generation
    await start_generation(
        task_id=task["id"],
        prompt=req.prompt,
        scene_duration=req.scene_duration,
        num_inference_steps=req.num_inference_steps,
        guidance_scale=req.guidance_scale,
        resolution=req.resolution,
    )

    return GenerationResponse(
        task_id=task["id"],
        status=task["status"],
        prompt=task["prompt"],
        created_at=task["created_at"],
    )


# ──────────────────────────────────────────────
# Task Management
# ──────────────────────────────────────────────

@router.get("/tasks", response_model=list[TaskListItem], tags=["Tasks"])
async def list_tasks(user: dict = Depends(get_current_user)):
    """List all tasks for the current user."""
    tasks = await database.get_user_tasks(user["id"])
    result = []
    for t in tasks:
        thumbnail_url = None
        if t.get("thumbnail_path") and Path(t["thumbnail_path"]).exists():
            thumbnail_url = f"/api/tasks/{t['id']}/thumbnail"
        result.append(TaskListItem(
            id=t["id"],
            prompt=t["prompt"],
            status=t["status"],
            progress=t["progress"],
            resolution=t["resolution"],
            created_at=t["created_at"],
            completed_at=t.get("completed_at"),
            thumbnail_url=thumbnail_url,
        ))
    return result


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, tags=["Tasks"])
async def get_task_status(task_id: str, user: dict = Depends(get_current_user)):
    """Get detailed status of a specific task."""
    task = await database.get_task(task_id)
    if not task or task["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Task not found")

    video_url = None
    thumbnail_url = None

    if task["status"] == "completed" and task.get("video_path"):
        if Path(task["video_path"]).exists():
            video_url = f"/api/tasks/{task_id}/video"
    if task.get("thumbnail_path") and Path(task["thumbnail_path"]).exists():
        thumbnail_url = f"/api/tasks/{task_id}/thumbnail"

    return TaskStatusResponse(
        id=task["id"],
        prompt=task["prompt"],
        status=task["status"],
        progress=task["progress"],
        progress_message=task["progress_message"] or "",
        scene_duration=task["scene_duration"],
        resolution=task["resolution"],
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
        error=task.get("error"),
    )


@router.get("/tasks/{task_id}/video", tags=["Tasks"])
async def download_video(task_id: str, user: dict = Depends(get_user_from_token_param)):
    """Download or stream the generated video. Uses ?token= query param for auth
    because browser video elements cannot send Authorization headers."""
    task = await database.get_task(task_id)
    if not task or task["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "completed" or not task.get("video_path"):
        raise HTTPException(status_code=400, detail="Video not ready")

    video_path = Path(task["video_path"])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"video_{task_id[:8]}.mp4",
    )


@router.get("/tasks/{task_id}/thumbnail", tags=["Tasks"])
async def get_thumbnail(task_id: str, user: dict = Depends(get_user_from_token_param)):
    """Get the thumbnail image. Uses ?token= query param for auth
    because browser img elements cannot send Authorization headers."""
    task = await database.get_task(task_id)
    if not task or task["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.get("thumbnail_path"):
        raise HTTPException(status_code=404, detail="No thumbnail available")

    thumb_path = Path(task["thumbnail_path"])
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")

    return FileResponse(path=str(thumb_path), media_type="image/png")


@router.delete("/tasks/{task_id}", response_model=MessageResponse, tags=["Tasks"])
async def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    """Delete a task and all its generated files."""
    task = await database.get_task(task_id)
    if not task or task["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Task not found")

    # Remove files
    task_dir = TASKS_DIR / task_id
    if task_dir.exists():
        shutil.rmtree(str(task_dir))

    # Remove database record
    await database.delete_task(task_id)

    return MessageResponse(message="Task deleted successfully")
