"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional


# ──────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    created_at: str


# ──────────────────────────────────────────────
# Generation
# ──────────────────────────────────────────────

class GenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=2000,
                        description="Text to convert into a video")
    scene_duration: float = Field(default=3.0, ge=1.0, le=10.0,
                                  description="Duration per scene in seconds")
    num_inference_steps: int = Field(default=30, ge=10, le=100,
                                     description="Number of diffusion steps (higher = better quality, slower)")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0,
                                   description="How closely to follow the prompt")
    resolution: int = Field(default=768, description="Image resolution",
                            json_schema_extra={"enum": [512, 768, 1024]})


class GenerationResponse(BaseModel):
    task_id: str
    status: str
    prompt: str
    created_at: str


class TaskStatusResponse(BaseModel):
    id: str
    prompt: str
    status: str
    progress: float
    progress_message: str
    scene_duration: float
    resolution: int
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class TaskListItem(BaseModel):
    id: str
    prompt: str
    status: str
    progress: float
    resolution: int
    created_at: str
    completed_at: Optional[str] = None
    thumbnail_url: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    model_loaded: bool
    model_id: str


class MessageResponse(BaseModel):
    message: str
