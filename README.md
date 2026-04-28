# 🎬 Text-to-Video Studio

AI-powered text-to-video generation platform. Enter descriptive text, and the app generates stunning images for each sentence, converts text to speech narration, and combines everything into a downloadable video.

## ✨ Features

- **AI Image Generation** — Stable Diffusion (Playground v2) generates high-quality images
- **Text-to-Speech** — Google TTS creates natural narration for each scene
- **Automatic Video Composition** — MoviePy combines images + audio into final video
- **User Authentication** — JWT-based login/register with secure password hashing
- **Real-time Progress** — Live progress tracking during generation
- **Configurable Settings** — Resolution (512/768/1024), scene duration, quality steps
- **Video Gallery** — Browse and manage all your generated videos
- **Premium Dark UI** — Modern glassmorphism design with animations

## 🛠️ Prerequisites

- **Python 3.10+**
- **NVIDIA GPU** with CUDA support (8GB+ VRAM recommended)
- **FFmpeg** installed and on PATH ([download](https://ffmpeg.org/download.html))

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env and change SECRET_KEY to a random string
```

### 3. Run the Application

```bash
python run.py
```

### 4. Open in Browser

Navigate to **http://localhost:8000**

1. Create an account (Register)
2. Enter your text prompt
3. Adjust settings (resolution, duration, etc.)
4. Click **Generate Video**
5. Watch progress in real-time
6. Download your video!

## 📁 Project Structure

```
text__to__video/
├── run.py                  # Entry point
├── .env.example            # Config template
├── backend/
│   ├── main.py             # FastAPI app
│   ├── config.py           # Configuration
│   ├── auth.py             # JWT authentication
│   ├── models.py           # Pydantic schemas
│   ├── database.py         # SQLite database
│   ├── pipeline.py         # Video generation engine
│   ├── routes.py           # API endpoints
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Single-page app
│   ├── styles.css          # Premium dark UI
│   └── app.js              # Client logic
└── data/                   # Generated at runtime
    ├── database.db
    └── tasks/{task_id}/
        ├── images/
        ├── audio/
        └── video/
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Current user |
| POST | `/api/generate` | Submit generation |
| GET | `/api/tasks` | List all tasks |
| GET | `/api/tasks/{id}` | Task status |
| GET | `/api/tasks/{id}/video` | Download video |
| DELETE | `/api/tasks/{id}` | Delete task |
| GET | `/api/health` | Server health |

## ⚙️ Configuration

All settings in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_ID` | `playground-v2` | HuggingFace model ID |
| `DEVICE` | `cuda` | `cuda` or `cpu` |
| `DEFAULT_RESOLUTION` | `768` | Default image size |
| `DEFAULT_SCENE_DURATION` | `3.0` | Seconds per scene |
| `SECRET_KEY` | — | JWT secret (change this!) |

## 🐛 Troubleshooting

**CUDA not available**: Ensure NVIDIA drivers + CUDA toolkit are installed. Check with `python -c "import torch; print(torch.cuda.is_available())"`.

**Model download slow**: The model (~6GB) downloads on first generation. Be patient.

**FFmpeg not found**: Install FFmpeg and add to PATH. MoviePy requires it for video encoding.

## 📝 License

MIT
