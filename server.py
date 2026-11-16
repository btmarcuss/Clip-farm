import os
import uuid
import threading
import json
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    OUTPUT_DIR, MAX_CLIPS, DEFAULT_LAYOUT, ENABLE_SUBTITLES, AUTO_POST,
    BASE_DIR, GEMINI_API_KEY, TIKTOK_ACCESS_TOKEN, TIKTOK_PRIVACY_LEVEL, WHISPER_MODEL,
    SERVER_HOST, SERVER_PORT
)
from downloader import download_youtube_video
from audio_analyzer import detect_audio_spikes
from transcriber import transcribe_audio
from viral_analyzer import find_viral_moments
from subtitles_generator import generate_tiktok_ass_subtitles
from video_editor import create_vertical_clip, generate_clip_thumbnail
from auto_publisher import publish_clip_to_tiktok

app = FastAPI(title="Clip Farm Studio Pro", version="2.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: Dict[str, Dict[str, Any]] = {}

class JobRequest(BaseModel):
    url: str
    clips: int = MAX_CLIPS
    layout: str = DEFAULT_LAYOUT
    subtitles: bool = ENABLE_SUBTITLES
    auto_post: bool = AUTO_POST

class ConfigUpdate(BaseModel):
    gemini_key: str = ""
    tiktok_token: str = ""
    privacy: str = "SELF_ONLY"
    whisper_model: str = "base"

def run_job_pipeline(job_id: str, req: JobRequest):
    job = JOBS[job_id]
    try:
        job["status"] = "downloading"
        job["progress"] = 15
        job["message"] = "1/4 📥 Baixando vídeo e extraindo áudio do YouTube..."
        media = download_youtube_video(req.url)
        job["video_id"] = media["id"]
        job["title"] = media["title"]

        job["status"] = "analyzing_audio"
        job["progress"] = 30
        job["message"] = "2/4 🔊 Mapeando picos de energia e reações sonoras..."
        spikes = detect_audio_spikes(media["audio_path"])

        job["status"] = "transcribing"
        job["progress"] = 50
        job["message"] = "2/4 🎙️ Transcrevendo com Whisper IA (palavra por palavra)..."
        transcript = transcribe_audio(media["audio_path"])

        job["status"] = "ai_thinking"
        job["progress"] = 70
        job["message"] = "3/4 🧠 IA Gemini selecionando os momentos de maior retenção..."
        viral_clips = find_viral_moments(transcript, max_clips=req.clips, audio_spikes=spikes)

        job["status"] = "rendering"
        job["progress"] = 85
        job["message"] = f"4/4 ✂️ Renderizando {len(viral_clips)} cortes verticais 9:16..."

        video_output_dir = OUTPUT_DIR / media["id"]
        video_output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        for idx, clip in enumerate(viral_clips, 1):
            clip_base = f"corte_{idx:02d}"
            v_out = video_output_dir / f"{clip_base}.mp4"
            t_out = video_output_dir / f"{clip_base}_thumb.jpg"
            sub_path = None

            if req.subtitles:
                ass_file = video_output_dir / f"{clip_base}.ass"
                sub_path = generate_tiktok_ass_subtitles(
                    segments_with_words=transcript,
                    clip_start=clip["start_time"],
                    clip_end=clip["end_time"],
                    output_ass_path=str(ass_file)
                )

            create_vertical_clip(
                video_path=media["video_path"],
                start_time=clip["start_time"],
                end_time=clip["end_time"],
                output_path=str(v_out),
                subtitles_ass_path=sub_path,
                layout=req.layout
            )

            generate_clip_thumbnail(
                video_path=str(v_out),
                timestamp=1.0,
                output_thumb_path=str(t_out)
            )

            post_status = None
            if req.auto_post:
                job["message"] = f"📲 Postando corte #{idx} no TikTok..."
                post_status = publish_clip_to_tiktok(
                    video_path=str(v_out),
                    title=clip.get("suggested_title", "Corte Viral"),
                    hashtags=clip.get("hashtags", [])
                )

            results.append({
                "clip_number": idx,
                "video_url": f"/api/media/{media['id']}/{clip_base}.mp4",
                "thumb_url": f"/api/media/{media['id']}/{clip_base}_thumb.jpg",
                "start_time": clip["start_time"],
                "end_time": clip["end_time"],
                "duration": round(clip["end_time"] - clip["start_time"], 2),
                "title": clip.get("suggested_title", "Corte Viral"),
                "hook": clip.get("hook_phrase", ""),
                "reason": clip.get("reason", ""),
                "hashtags": clip.get("hashtags", []),
                "auto_post_status": post_status
            })

        with open(video_output_dir / "postagens.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Processamento concluído!" + (" Cortes postados no TikTok!" if req.auto_post else "")
        job["results"] = results

    except Exception as e:
        job["status"] = "failed"
        job["progress"] = 0
        job["message"] = f"Erro no processamento: {str(e)}"

@app.post("/api/jobs")
def create_job(req: JobRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 5,
        "message": "Tarefa adicionada na fila de processamento...",
        "results": []
    }
    background_tasks.add_task(run_job_pipeline, job_id, req)
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return JOBS[job_id]

@app.get("/api/history")
def get_history():
    history = []
    if OUTPUT_DIR.exists():
        for vid_dir in sorted(OUTPUT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if vid_dir.is_dir():
                meta_file = vid_dir / "postagens.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            clips = json.load(f)
                            history.append({
                                "video_id": vid_dir.name,
                                "clips_count": len(clips),
                                "clips": clips
                            })
                    except Exception:
                        pass
    return history

@app.get("/api/config")
def get_app_config():
    """Retorna o status atual das configurações sem expor o segredo completo."""
    env_file = BASE_DIR / ".env"
    gemini_set = bool(os.getenv("GEMINI_API_KEY", ""))
    tiktok_set = bool(os.getenv("TIKTOK_ACCESS_TOKEN", ""))
    return {
        "has_gemini_key": gemini_set,
        "has_tiktok_token": tiktok_set,
        "privacy": os.getenv("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY"),
        "whisper_model": os.getenv("WHISPER_MODEL", "base")
    }

@app.post("/api/config")
def save_app_config(cfg: ConfigUpdate):
    """Permite atualizar as chaves de API direto pela interface visual."""
    env_file = BASE_DIR / ".env"
    lines = []
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated = {
        "GEMINI_API_KEY": cfg.gemini_key,
        "TIKTOK_ACCESS_TOKEN": cfg.tiktok_token,
        "TIKTOK_PRIVACY_LEVEL": cfg.privacy,
        "WHISPER_MODEL": cfg.whisper_model
    }

    new_lines = []
    existing_keys = set()
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            k = k.strip()
            if k in updated and updated[k]:
                new_lines.append(f"{k}={updated[k]}\n")
                os.environ[k] = updated[k]
                existing_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in updated.items():
        if k not in existing_keys and v:
            new_lines.append(f"{k}={v}\n")
            os.environ[k] = v

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return {"success": True, "message": "Configurações salvas com sucesso!"}

@app.get("/api/media/{video_id}/{filename}")
def serve_media(video_id: str, filename: str):
    file_path = OUTPUT_DIR / video_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    media_type = "video/mp4" if filename.endswith(".mp4") else "image/jpeg"
    return FileResponse(file_path, media_type=media_type)

@app.get("/manifest.json")
def pwa_manifest():
    return JSONResponse({
        "name": "Clip Farm Studio",
        "short_name": "ClipFarm",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d0f12",
        "theme_color": "#ff0050",
        "orientation": "any"
    })

@app.get("/", response_class=HTMLResponse)
def index_page():
    html_file = BASE_DIR / "static" / "index.html"
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Clip Farm Server Online</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.py:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
