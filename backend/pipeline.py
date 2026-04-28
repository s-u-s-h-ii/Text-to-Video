"""
Video generation pipeline.
Refactored from the original new_text_to_video.py script.
Handles: text splitting -> image generation -> TTS -> video composition.
"""

import os
import re
import asyncio
import logging
import torch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from backend.config import (
    MODEL_ID, DEVICE, TORCH_DTYPE, TASKS_DIR,
    VIDEO_FPS, MAX_SENTENCES
)
from backend import database

logger = logging.getLogger("pipeline")

# Thread pool for running blocking GPU operations
_executor = ThreadPoolExecutor(max_workers=1)


class ModelManager:
    """
    Singleton manager for the Stable Diffusion pipeline.
    Lazy-loads the model on first use to avoid slow startup.
    """
    _instance = None
    _pipe = None
    _is_loading = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_loaded(self) -> bool:
        return self._pipe is not None

    @property
    def is_loading(self) -> bool:
        return self._is_loading

    def load_model(self):
        """Load the diffusion pipeline (blocking, run in thread)."""
        if self._pipe is not None:
            return

        self._is_loading = True
        logger.info(f"Loading model: {MODEL_ID}")

        try:
            from diffusers import DiffusionPipeline

            dtype = torch.float16 if TORCH_DTYPE == "float16" else torch.float32
            device = DEVICE if torch.cuda.is_available() else "cpu"

            if device == "cpu":
                dtype = torch.float32
                logger.warning("CUDA not available, falling back to CPU (will be slow)")

            self._pipe = DiffusionPipeline.from_pretrained(
                MODEL_ID,
                torch_dtype=dtype,
                variant="fp16" if dtype == torch.float16 else None,
            )

            if device == "cuda":
                self._pipe = self._pipe.to("cuda")
                # Enable memory-efficient attention if available
                try:
                    self._pipe.enable_xformers_memory_efficient_attention()
                    logger.info("xformers memory-efficient attention enabled")
                except Exception:
                    logger.info("xformers not available, using default attention")
            else:
                # For CPU, enable sequential offloading to save memory
                try:
                    self._pipe.enable_model_cpu_offload()
                except Exception:
                    pass

            logger.info(f"Model loaded successfully on {device}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
        finally:
            self._is_loading = False

    def generate_image(self, prompt: str, resolution: int = 768,
                       num_inference_steps: int = 30,
                       guidance_scale: float = 7.5):
        """Generate a single image from a text prompt."""
        if self._pipe is None:
            self.load_model()

        image = self._pipe(
            prompt,
            width=resolution,
            height=resolution,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        ).images[0]

        return image

    def unload(self):
        """Free GPU memory."""
        if self._pipe is not None:
            del self._pipe
            self._pipe = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Model unloaded")


def split_text_to_sentences(text: str) -> list[str]:
    """
    Split text into sentences, handling edge cases.
    Returns non-empty, stripped sentences up to MAX_SENTENCES.
    """
    # Split on period, exclamation, question mark
    raw = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in raw if s.strip() and len(s.strip()) > 2]

    if not sentences:
        sentences = [text.strip()]

    return sentences[:MAX_SENTENCES]


def _generate_video_sync(
    task_id: str,
    prompt: str,
    scene_duration: float,
    num_inference_steps: int,
    guidance_scale: float,
    resolution: int,
):
    """
    Synchronous video generation function.
    Runs in a thread pool to avoid blocking the event loop.
    """
    import moviepy as mpe
    from gtts import gTTS
    from PIL import Image

    task_dir = TASKS_DIR / task_id
    image_dir = task_dir / "images"
    audio_dir = task_dir / "audio"
    video_dir = task_dir / "video"

    for d in [image_dir, audio_dir, video_dir]:
        d.mkdir(parents=True, exist_ok=True)

    sentences = split_text_to_sentences(prompt)
    total_steps = len(sentences) * 3 + 1  # image + audio + clip per sentence + final merge
    current_step = 0

    def update_progress(message: str):
        nonlocal current_step
        current_step += 1
        progress = min((current_step / total_steps) * 100, 99.0)
        # Use synchronous database update via asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            database.update_task_progress(task_id, progress, message)
        )
        loop.close()

    try:
        model = ModelManager.get_instance()

        # ── Step 1: Generate images ──
        image_paths = []
        for i, sentence in enumerate(sentences):
            update_progress(f"Generating image {i + 1}/{len(sentences)}...")
            logger.info(f"[{task_id}] Generating image {i + 1}: {sentence[:50]}...")

            image = model.generate_image(
                prompt=sentence,
                resolution=resolution,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )
            img_path = image_dir / f"scene_{i:03d}.png"
            image.save(str(img_path))
            image_paths.append(str(img_path))

            # Free memory after each generation
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # ── Step 2: Generate TTS audio ──
        audio_paths = []
        for i, sentence in enumerate(sentences):
            update_progress(f"Generating audio {i + 1}/{len(sentences)}...")
            logger.info(f"[{task_id}] Generating audio {i + 1}: {sentence[:50]}...")

            tts = gTTS(sentence, lang="en")
            audio_path = audio_dir / f"audio_{i:03d}.mp3"
            tts.save(str(audio_path))
            audio_paths.append(str(audio_path))

        # ── Step 3: Create video clips with audio ──
        video_clips = []
        for i in range(len(sentences)):
            update_progress(f"Composing scene {i + 1}/{len(sentences)}...")
            logger.info(f"[{task_id}] Creating clip {i + 1}...")

            audio_clip = mpe.AudioFileClip(str(audio_paths[i]))
            # Use the longer of scene_duration or audio duration
            clip_duration = max(scene_duration, audio_clip.duration + 0.5)

            img_clip = mpe.ImageClip(str(image_paths[i]), duration=clip_duration)
            img_clip = img_clip.with_audio(audio_clip)
            img_clip = img_clip.resized(width=resolution if resolution % 2 == 0 else resolution - 1)
            video_clips.append(img_clip)

        # ── Step 4: Concatenate and export ──
        update_progress("Rendering final video...")
        logger.info(f"[{task_id}] Rendering final video...")

        final_video = mpe.concatenate_videoclips(video_clips, method="compose")
        output_path = video_dir / "final_video.mp4"
        final_video.write_videofile(
            str(output_path),
            codec="libx264",
            fps=VIDEO_FPS,
            audio_codec="aac",
            logger=None,  # Suppress moviepy's verbose logging
        )

        # Cleanup moviepy objects
        for clip in video_clips:
            clip.close()
        final_video.close()

        # Save first image as thumbnail
        thumbnail_path = str(image_paths[0]) if image_paths else None

        # Mark complete
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            database.complete_task(task_id, str(output_path), thumbnail_path)
        )
        loop.close()

        logger.info(f"[{task_id}] Video generation complete!")

    except Exception as e:
        logger.error(f"[{task_id}] Generation failed: {e}", exc_info=True)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(database.fail_task(task_id, str(e)))
        loop.close()


async def start_generation(
    task_id: str,
    prompt: str,
    scene_duration: float,
    num_inference_steps: int,
    guidance_scale: float,
    resolution: int,
):
    """
    Start video generation in a background thread.
    Returns immediately so the API can respond with the task_id.
    """
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _generate_video_sync,
        task_id, prompt, scene_duration,
        num_inference_steps, guidance_scale, resolution,
    )
