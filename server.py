import os
import sys
import time
import socket
import signal
import uuid
import threading
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import deque

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
from tiktok_auth import (
    get_tiktok_session, save_tiktok_session, save_tiktok_credentials,
    remove_tiktok_session, verify_tiktok_sessionid
)

app = FastAPI(title="Clip Farm Studio Pro", version="2.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Buffer de Logs em memória (armazena os últimos 200 eventos do terminal)
MAX_LOGS = 200
SYSTEM_LOGS = deque(maxlen=MAX_LOGS)

def log_event(message: str):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    SYSTEM_LOGS.append(entry)
    print(entry)

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
        log_event(f"🚀 Iniciando processamento do job #{job_id} para URL: {req.url}")
        job["status"] = "downloading"
        job["progress"] = 15
        job["message"] = "1/4 📥 Baixando vídeo e áudio do YouTube..."
        log_event("📥 Baixando vídeo do YouTube em até 1080p...")
        media = download_youtube_video(req.url)
        job["video_id"] = media["id"]
        job["title"] = media["title"]
        log_event(f"🎬 Vídeo baixado: '{media['title']}' (ID: {media['id']})")

        job["status"] = "analyzing_audio"
        job["progress"] = 30
        job["message"] = "2/4 🔊 Mapeando picos de energia e reações sonoras..."
        log_event("🔊 Analisando amplitude de áudio e momentos de grito/risada...")
        spikes = detect_audio_spikes(media["audio_path"])
        log_event(f"⚡ Picos de som detectados: {len(spikes)} momentos-chave.")

        job["status"] = "transcribing"
        job["progress"] = 50
        job["message"] = "2/4 🎙️ Transcrevendo com Faster-Whisper IA..."
        log_event("🎙️ Transcrevendo áudio com timestamps por palavra...")
        transcript = transcribe_audio(media["audio_path"])
        log_event(f"✅ Transcrição concluída: {len(transcript)} segmentos de fala mapeados.")

        job["status"] = "ai_thinking"
        job["progress"] = 70
        job["message"] = "3/4 🧠 IA Gemini selecionando os momentos de maior retenção..."
        log_event("🧠 Solicitando à IA Gemini a análise de ganchos (hooks) e retenção viral...")
        viral_clips = find_viral_moments(transcript, max_clips=req.clips, audio_spikes=spikes)
        log_event(f"🎯 IA selecionou {len(viral_clips)} cortes com alto potencial viral.")

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

            log_event(f"✂️ Renderizando Corte #{idx} ({clip['start_time']}s até {clip['end_time']}s) - Layout: {req.layout}")

            if req.subtitles:
                ass_file = video_output_dir / f"{clip_base}.ass"
                sub_path = generate_tiktok_ass_subtitles(
                    segments_with_words=transcript,
                    clip_start=clip["start_time"],
                    clip_end=clip["end_time"],
                    output_ass_path=str(ass_file)
                )
                log_event(f"📝 Legendas dinâmicas estilo Hormozi geradas para corte #{idx}")

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
                log_event(f"📲 Postando Corte #{idx} no TikTok automaticamente...")
                job["message"] = f"📲 Postando corte #{idx} no TikTok..."
                post_status = publish_clip_to_tiktok(
                    video_path=str(v_out),
                    title=clip.get("suggested_title", "Corte Viral"),
                    hashtags=clip.get("hashtags", [])
                )
                log_event(f"✅ Status da postagem do corte #{idx}: {post_status.get('status')}")

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
        log_event(f"🎉 Job #{job_id} concluído com sucesso total! Clipes salvos em: {video_output_dir.name}")

    except Exception as e:
        err_msg = f"Erro no processamento: {str(e)}"
        job["status"] = "failed"
        job["progress"] = 0
        job["message"] = err_msg
        log_event(f"❌ [FALHA] {err_msg}")

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

class TikTokUserLoginRequest(BaseModel):
    username: str
    password: str

class TikTokLoginRequest(BaseModel):
    session_id: str = ""
    access_token: str = ""

@app.get("/api/tiktok/status")
def tiktok_status():
    """Retorna se há uma conta do TikTok conectada e os dados do usuário."""
    session = get_tiktok_session()
    auth_type = session.get("auth_type", "none")
    username = session.get("username", "")
    
    connected = bool(username or session.get("session_id") or session.get("access_token") or os.getenv("TIKTOK_ACCESS_TOKEN", ""))
    
    return {
        "connected": connected,
        "method": auth_type,
        "username": username or "Conta Conectada",
        "nickname": session.get("nickname", f"@{username}" if username else "Criador TikTok")
    }

@app.post("/api/tiktok/login-user")
def tiktok_login_user(req: TikTokUserLoginRequest):
    """Realiza o login no TikTok utilizando Usuário/E-mail e Senha."""
    user = req.username.strip()
    pwd = req.password.strip()

    if not user or not pwd:
        raise HTTPException(status_code=400, detail="Por favor, preencha o usuário e a senha.")

    session = save_tiktok_credentials(username=user, password=pwd)
    log_event(f"🔑 Login do TikTok salvo para o usuário: @{session.get('username')}")
    
    return {
        "success": True,
        "message": f"Login do TikTok configurado com sucesso para @{session.get('username')}!",
        "username": session.get("username")
    }

@app.post("/api/tiktok/login")
def tiktok_login(req: TikTokLoginRequest):
    """Realiza a conexão da conta do TikTok via Session ID ou Access Token."""
    sid = req.session_id.strip()
    token = req.access_token.strip()

    if sid:
        verification = verify_tiktok_sessionid(sid)
        if verification["valid"]:
            save_tiktok_session(
                session_id=sid,
                username=verification.get("username", "conectado")
            )
            log_event(f"🔑 Conta do TikTok conectada com sucesso (@{verification.get('username')})")
            return {
                "success": True,
                "message": f"Conectado com sucesso como @{verification.get('username')}!",
                "username": verification.get("username")
            }
        else:
            raise HTTPException(status_code=400, detail=verification.get("error", "Session ID inválido"))

    if token:
        save_tiktok_session(access_token=token)
        log_event("🔑 Token de API do TikTok salvo e ativado.")
        return {"success": True, "message": "Token de API do TikTok conectado com sucesso!"}

    raise HTTPException(status_code=400, detail="Forneça um Session ID ou um Access Token do TikTok.")

@app.post("/api/tiktok/logout")
def tiktok_logout():
    """Desconecta a conta do TikTok."""
    remove_tiktok_session()
    log_event("🚪 Conta do TikTok desconectada.")
    return {"success": True, "message": "Conta desconectada com sucesso."}

@app.get("/api/logs")
def get_logs():
    """Retorna os logs em tempo real para exibir no terminal embutido do site."""
    return list(SYSTEM_LOGS)

@app.post("/api/shutdown")
def shutdown_server():
    """Desliga o servidor graciosamente a partir do site."""
    log_event("🛑 Comando de desligamento recebido do site. Encerrando servidor em 1 segundo...")
    
    def do_exit():
        time.sleep(1.2)
        os._exit(0)

    threading.Thread(target=do_exit, daemon=True).start()
    return {"success": True, "message": "Servidor desligando. Você já pode fechar esta aba."}

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

@app.get("/api/network-info")
def network_info():
    ip = get_local_ip()
    return {
        "local_ip": ip,
        "port": SERVER_PORT,
        "desktop_url": f"http://localhost:{SERVER_PORT}",
        "mobile_url": f"http://{ip}:{SERVER_PORT}"
    }

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
    return {
        "has_gemini_key": bool(os.getenv("GEMINI_API_KEY", "")),
        "has_tiktok_token": bool(os.getenv("TIKTOK_ACCESS_TOKEN", "")),
        "privacy": os.getenv("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY"),
        "whisper_model": os.getenv("WHISPER_MODEL", "base")
    }

@app.post("/api/config")
def save_app_config(cfg: ConfigUpdate):
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

    log_event("⚙️ Configurações de API salvas via painel web.")
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
