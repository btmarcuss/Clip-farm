import os
import sys

# Garante codificacao UTF-8 universal no Windows para evitar erros de charmap
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import time
import socket
import signal
import uuid
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List
from collections import deque

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import io
from config import (
    OUTPUT_DIR, TEMP_DIR, MAX_CLIPS, DEFAULT_LAYOUT, ENABLE_SUBTITLES, AUTO_POST,
    BASE_DIR, GEMINI_API_KEY, TIKTOK_ACCESS_TOKEN, TIKTOK_PRIVACY_LEVEL, WHISPER_MODEL,
    SERVER_HOST, SERVER_PORT
)
from security import (
    redact_sensitive, safe_media_path, validate_youtube_url, sanitize_env_value,
    validate_layout, validate_privacy, validate_whisper_model,
    is_private_or_local_ip, is_allowed_origin, RateLimiter, SECURITY_HEADERS
)
from legal_compliance import (
    get_legal_documents, get_cookie_consent, save_cookie_consent,
    submit_lgpd_request, export_user_data, delete_all_user_data
)
from downloader import download_youtube_video
from audio_analyzer import detect_audio_spikes
from transcriber import transcribe_audio
from viral_analyzer import find_viral_moments
from subtitles_generator import generate_tiktok_ass_subtitles
from video_editor import create_vertical_clip, generate_clip_thumbnail
from auto_publisher import (
    publish_clip_to_tiktok, publish_clips_batch, open_tiktok_login_window, is_tiktok_browser_logged_in
)
from tiktok_auth import (
    get_tiktok_session, save_tiktok_session, save_tiktok_credentials,
    save_tiktok_phone_login, save_tiktok_google_login,
    remove_tiktok_session, verify_tiktok_sessionid
)

# Desabilita Swagger/OpenAPI público para não expor mapa de rotas na rede
app = FastAPI(
    title="Clip Farm Studio Pro",
    version="2.4.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _detect_local_ip_boot() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


_BOOT_IP = _detect_local_ip_boot()
ALLOWED_ORIGINS = {
    f"http://localhost:{SERVER_PORT}",
    f"http://127.0.0.1:{SERVER_PORT}",
    f"http://{_BOOT_IP}:{SERVER_PORT}",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_RATE_LIMITER = RateLimiter()

# Buffer de Logs em memória (armazena os últimos 200 eventos do terminal)
MAX_LOGS = 200
SYSTEM_LOGS = deque(maxlen=MAX_LOGS)


def log_event(message: str):
    timestamp = time.strftime("%H:%M:%S")
    # DLP: mascara automaticamente chaves, tokens, e-mails e telefones antes de registrar
    safe_msg = redact_sensitive(message)
    entry = f"[{timestamp}] {safe_msg}"
    SYSTEM_LOGS.append(entry)
    print(entry)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"

    # 1. Bloqueio de acessos vindos de fora da rede local (Anti-Invasão Externa)
    if not is_private_or_local_ip(client_ip):
        log_event(f"🛡️ [BLOQUEADO] Tentativa de acesso de IP externo: {client_ip}")
        return JSONResponse(status_code=403, content={"detail": "Acesso permitido apenas na rede local."})

    # 2. Proteção Anti-CSRF em rotas mutantes (POST/PUT/DELETE)
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origin = request.headers.get("origin") or request.headers.get("referer") or ""
        if origin and not is_allowed_origin(origin, ALLOWED_ORIGINS):
            log_event(f"🛡️ [CSRF BLOQUEADO] Origem não autorizada ({origin}) de {client_ip}")
            return JSONResponse(status_code=403, content={"detail": "Origem da requisição não autorizada."})

    # 3. Rate Limiting por IP (Anti-Flood / Anti-Brute-Force)
    path = request.url.path
    is_sensitive = path.startswith(("/api/tiktok/", "/api/config", "/api/shutdown", "/api/jobs", "/api/clips/", "/api/lgpd/"))
    if is_sensitive and request.method == "POST":
        if not _RATE_LIMITER.allow(f"strict:{client_ip}", max_requests=20, window_seconds=60):
            log_event(f"🛡️ [RATE LIMIT] Excesso de requisições sensíveis de {client_ip} em {path}")
            return JSONResponse(status_code=429, content={"detail": "Muitas requisições. Aguarde um minuto."})
    else:
        if not _RATE_LIMITER.allow(f"gen:{client_ip}", max_requests=180, window_seconds=60):
            return JSONResponse(status_code=429, content={"detail": "Limite de requisições excedido."})

    response = await call_next(request)

    # 4. Cabeçalhos HTTP de Hardening (Anti-XSS, Anti-Clickjacking, Anti-MIME Sniffing)
    for k, v in SECURITY_HEADERS.items():
        if k == "Cache-Control" and path.startswith("/api/media/"):
            continue
        response.headers[k] = v
    return response

JOBS: Dict[str, Dict[str, Any]] = {}

class JobRequest(BaseModel):
    url: str
    clips: int = MAX_CLIPS
    layout: str = DEFAULT_LAYOUT
    subtitles: bool = ENABLE_SUBTITLES
    auto_post: bool = AUTO_POST
    delete_after: bool = True  # Não guarda os vídeos no disco: apaga após postar
    copyright_confirmed: bool = True  # Declaração de direitos autorais (Lei nº 9.610/1998)

class ConfigUpdate(BaseModel):
    gemini_key: str = ""
    tiktok_token: str = ""
    privacy: str = "SELF_ONLY"
    whisper_model: str = "base"

def run_job_pipeline(job_id: str, req: JobRequest):
    job = JOBS[job_id]
    try:
        log_event(f"🚀 Iniciando processamento do job #{job_id} para URL: {req.url}")
        t_job_start = time.monotonic()
        job["status"] = "downloading"
        job["progress"] = 15
        job["message"] = "1/4 📥 Baixando vídeo em 720p H.264..."
        log_event("📥 Baixando vídeo do YouTube em 720p H.264 (SSD local)...")
        media = download_youtube_video(req.url)
        job["video_id"] = media["id"]
        job["title"] = media["title"]
        log_event(f"🎬 Vídeo 720p pronto: '{media['title']}' (ID: {media['id']})")

        job["status"] = "analyzing_audio"
        job["progress"] = 30

        yt_transcript = media.get("youtube_transcript") or []
        spikes_result = [None]
        transcript_result = [yt_transcript if yt_transcript else None]

        if yt_transcript:
            job["message"] = "2/4 ⚡ Transcrição instantânea obtida do YouTube! Mapeando picos de áudio..."
            log_event(f"⚡ Transcrição instantânea via YouTube ({len(yt_transcript)} segmentos) — Whisper dispensado!")
            spikes_result[0] = detect_audio_spikes(media["audio_path"], top_n=60)
            log_event(f"⚡ Picos de som detectados: {len(spikes_result[0])} momentos-chave ao longo do vídeo.")
        else:
            job["message"] = "2/4 ⚡ Analisando áudio e transcrevendo com Whisper em paralelo..."
            log_event("⚡ Vídeo sem legenda nativa no YouTube; iniciando análise de áudio e Faster-Whisper em paralelo...")

            def _analyze():
                spikes_result[0] = detect_audio_spikes(media["audio_path"], top_n=60)
                log_event(f"⚡ Picos de som detectados: {len(spikes_result[0])} momentos-chave ao longo do vídeo.")

            def _transcribe():
                transcript_result[0] = transcribe_audio(media["audio_path"])
                log_event(f"✅ Transcrição concluída: {len(transcript_result[0])} segmentos mapeados.")

            t_analyze = threading.Thread(target=_analyze)
            t_transcribe = threading.Thread(target=_transcribe)
            t_analyze.start()
            t_transcribe.start()
            t_analyze.join()
            t_transcribe.join()

        spikes = spikes_result[0]
        transcript = transcript_result[0]
        job["progress"] = 50

        job["status"] = "ai_thinking"
        job["progress"] = 60
        if req.clips == 0:
            job["message"] = "3/4 🔥 Modo Máximo: IA Gemini mapeando TODOS os momentos virais do vídeo inteiro..."
            log_event("🔥 Modo Máximo Possível: analisando o vídeo completo em blocos com IA Gemini...")
        else:
            job["message"] = f"3/4 🧠 IA Gemini selecionando até {req.clips} momentos de maior retenção..."
            log_event(f"🧠 Solicitando à IA Gemini até {req.clips} cortes com alto potencial viral...")
        viral_clips = find_viral_moments(transcript, max_clips=req.clips, audio_spikes=spikes)
        log_event(f"🎯 IA selecionou {len(viral_clips)} cortes com alto potencial viral.")

        job["status"] = "rendering"
        job["progress"] = 72
        job["message"] = f"4/4 ✂️ Renderizando {len(viral_clips)} cortes em paralelo (0/{len(viral_clips)})..."

        video_output_dir = OUTPUT_DIR / media["id"]
        video_output_dir.mkdir(parents=True, exist_ok=True)

        # ── OTIMIZAÇÃO: Gera os .ass de legenda (rápido, CPU bound) antes do rendering ──
        ass_paths = {}
        if req.subtitles:
            for idx, clip in enumerate(viral_clips, 1):
                clip_base = f"corte_{idx:02d}"
                ass_file = video_output_dir / f"{clip_base}.ass"
                ass_paths[idx] = generate_tiktok_ass_subtitles(
                    segments_with_words=transcript,
                    clip_start=clip["start_time"],
                    clip_end=clip["end_time"],
                    output_ass_path=str(ass_file)
                )

        # ── OTIMIZAÇÃO: Renderiza todos os cortes em paralelo (1 thread por corte) ──
        def render_clip(idx: int, clip: dict) -> dict:
            clip_base = f"corte_{idx:02d}"
            v_out = video_output_dir / f"{clip_base}.mp4"
            t_out = video_output_dir / f"{clip_base}_thumb.jpg"
            sub_path = ass_paths.get(idx)

            log_event(f"✂️ [Paralelo] Renderizando Corte #{idx} ({clip['start_time']}s→{clip['end_time']}s) Layout:{req.layout}")

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

            log_event(f"✅ Corte #{idx} renderizado com sucesso!")

            return {
                "clip_number": idx,
                "video_id": media["id"],
                "filename": f"{clip_base}.mp4",
                "video_url": f"/api/media/{media['id']}/{clip_base}.mp4",
                "thumb_url": f"/api/media/{media['id']}/{clip_base}_thumb.jpg",
                "file_exists": True,
                "start_time": clip["start_time"],
                "end_time": clip["end_time"],
                "duration": round(clip["end_time"] - clip["start_time"], 2),
                "title": clip.get("suggested_title", "Corte Viral"),
                "hook": clip.get("hook_phrase", ""),
                "reason": clip.get("reason", ""),
                "hashtags": clip.get("hashtags", []),
                "auto_post_status": None
            }

        results_map = {}
        done_render = 0
        total_render = max(len(viral_clips), 1)
        max_workers = min(len(viral_clips), 4)  # 720p30 + QSV permite até 4 renders paralelos leves
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(render_clip, idx, clip): idx for idx, clip in enumerate(viral_clips, 1)}
            for future in as_completed(futures):
                idx = futures[future]
                results_map[idx] = future.result()
                done_render += 1
                job["progress"] = 72 + int((done_render / total_render) * 18)
                job["message"] = f"4/4 ✂️ Renderizando cortes 720p ({done_render}/{total_render} prontos)..."

        results = [results_map[i] for i in sorted(results_map.keys())]

        # ── PUBLICAÇÃO EM LOTE NO TIKTOK (1 única sessão do Chrome para todos os cortes!) ──
        published_count = 0
        if req.auto_post:
            job["status"] = "publishing"
            job["progress"] = 90
            job["message"] = f"📲 Postando {len(results)} corte(s) em lote no TikTok..."
            log_event(f"📲 Iniciando publicação em lote de {len(results)} corte(s) na mesma sessão do Chrome...")

            batch_specs = [
                {
                    "video_path": str(video_output_dir / item["filename"]),
                    "title": item["title"],
                    "hashtags": item["hashtags"],
                }
                for item in results
            ]

            def _on_pub_progress(i: int, total: int, st: dict):
                job["progress"] = 90 + int((i / max(total, 1)) * 9)
                job["message"] = f"📲 Publicados {i}/{total} cortes no TikTok..."

            batch_statuses = publish_clips_batch(
                batch_specs,
                delete_after_post=req.delete_after,
                on_progress=_on_pub_progress,
            )

            for i, (item, post_status) in enumerate(zip(results, batch_statuses), 1):
                v_out = video_output_dir / item["filename"]
                item["auto_post_status"] = post_status
                item["file_exists"] = v_out.exists()
                if post_status.get("success") and post_status.get("status") == "published":
                    published_count += 1
                    log_event(f"✅ Corte #{i} publicado com sucesso no TikTok!")
                else:
                    log_event(f"⚠️ Corte #{i} não foi publicado ({post_status.get('error', 'erro desconhecido')}). Mantido para download.")

            # Limpa arquivos de origem temporários se delete_after estiver ativo e todos os cortes tiverem sido postados
            if req.delete_after and published_count == len(results):
                for src_p in (media.get("video_path"), media.get("audio_path")):
                    if src_p:
                        try:
                            Path(src_p).unlink(missing_ok=True)
                        except Exception:
                            pass
                for temp_f in TEMP_DIR.glob(f"{media['id']}.*"):
                    try:
                        temp_f.unlink(missing_ok=True)
                    except Exception:
                        pass

        with open(video_output_dir / "postagens.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        elapsed_total = round(time.monotonic() - t_job_start, 1)
        job["status"] = "completed"
        job["progress"] = 100
        if req.auto_post:
            if published_count == len(results):
                job["message"] = f"Concluído em {elapsed_total}s! Todos os {published_count} cortes 720p foram postados no TikTok!"
            elif published_count > 0:
                job["message"] = f"Concluído em {elapsed_total}s! {published_count}/{len(results)} postados; os demais estão disponíveis para baixar."
            else:
                job["message"] = f"Cortes 720p prontos em {elapsed_total}s! (Não foi possível postar automaticamente — disponíveis para download.)"
        else:
            job["message"] = f"Processamento concluído em {elapsed_total}s! Cortes 720p prontos para assistir e baixar."
        job["results"] = results
        log_event(f"🎉 Job #{job_id} concluído em {elapsed_total}s! Publicados: {published_count}/{len(results)} | Pasta: {video_output_dir.name}")

    except Exception as e:
        err_msg = f"Erro no processamento: {redact_sensitive(str(e))}"
        job["status"] = "failed"
        job["progress"] = 0
        job["message"] = err_msg
        log_event(f"❌ [FALHA] {err_msg}")

@app.post("/api/jobs")
def create_job(req: JobRequest, background_tasks: BackgroundTasks):
    if not req.copyright_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Confirme que possui os direitos autorais ou autorização de uso do vídeo (Lei nº 9.610/1998)."
        )
    try:
        req.url = validate_youtube_url(req.url)
    except ValueError as e:
        log_event(f"🛡️ [URL BLOQUEADA] {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # 0 = Modo Máximo Possível (calcula automaticamente p/ vídeo inteiro); 1..100 = quantidade exata
    req.clips = 0 if int(req.clips) <= 0 else min(int(req.clips), 100)
    req.layout = validate_layout(req.layout)

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

class TikTokPhoneLoginRequest(BaseModel):
    phone: str
    password: str = ""
    sms_code: str = ""

class TikTokGoogleLoginRequest(BaseModel):
    google_email: str
    auth_token: str = ""

class TikTokUserLoginRequest(BaseModel):
    username: str
    password: str

class TikTokLoginRequest(BaseModel):
    session_id: str = ""
    access_token: str = ""

@app.post("/api/tiktok/open-browser")
def tiktok_open_browser():
    """Abre uma janela real do Google Chrome na tela do usuário para login direto no TikTok."""
    def run_login():
        log_event("🌐 Abrindo janela do Google Chrome para login no TikTok...")
        res = open_tiktok_login_window()
        if res.get("logged_in"):
            log_event("🎉 Conta do TikTok conectada com sucesso no Navegador!")
        else:
            log_event("ℹ️ Janela de login do TikTok finalizada.")

    threading.Thread(target=run_login, daemon=True).start()
    return {"success": True, "message": "Janela do Google Chrome aberta! Faça seu login e resolva o captcha na tela."}

@app.get("/api/tiktok/browser-status")
def tiktok_browser_status():
    """Retorna se o navegador Chrome já possui sessão ativa do TikTok salva."""
    logged = is_tiktok_browser_logged_in()
    return {"browser_logged_in": logged}

@app.get("/api/tiktok/status")
def tiktok_status():
    """Retorna se há uma conta do TikTok conectada e os dados do usuário."""
    session = get_tiktok_session()
    auth_type = session.get("auth_type", "none")
    username = session.get("username", "")
    browser_logged = is_tiktok_browser_logged_in()

    connected = bool(browser_logged or username or session.get("session_id") or session.get("access_token") or os.getenv("TIKTOK_ACCESS_TOKEN", ""))

    return {
        "connected": connected,
        "browser_logged_in": browser_logged,
        "method": "chrome_browser" if browser_logged else auth_type,
        "username": username or ("Conta Conectada no Chrome" if browser_logged else "Não Conectado"),
        "nickname": session.get("nickname", f"@{username}" if username else ("TikTok Conectado" if browser_logged else "Desconectado"))
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

@app.post("/api/tiktok/login-phone")
def tiktok_login_phone(req: TikTokPhoneLoginRequest):
    """Realiza a conexão da conta do TikTok utilizando Número de Telefone."""
    phone = req.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Por favor, informe o número de telefone com DDD.")

    session = save_tiktok_phone_login(phone=phone, password=req.password, sms_code=req.sms_code)
    log_event(f"📱 Login com Número de Telefone salvo: {phone}")
    
    return {
        "success": True,
        "message": f"Telefone {phone} conectado com sucesso ao TikTok!",
        "username": session.get("username")
    }

@app.post("/api/tiktok/login-google")
def tiktok_login_google(req: TikTokGoogleLoginRequest):
    """Conecta a conta TikTok através da Conta Google (Google Sign-In)."""
    email = req.google_email.strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Por favor, informe um e-mail Google válido.")

    session = save_tiktok_google_login(google_email=email, auth_token=req.auth_token)
    log_event(f"🌐 Conta TikTok conectada via Google ({email})")
    
    return {
        "success": True,
        "message": f"Conta Google ({email}) conectada com sucesso ao TikTok!",
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
                        for c in clips:
                            c.setdefault("video_id", vid_dir.name)
                            fname = c.get("filename") or f"corte_{c.get('clip_number', 1):02d}.mp4"
                            c["filename"] = fname
                            c["file_exists"] = (vid_dir / fname).exists()
                        history.append({
                            "video_id": vid_dir.name,
                            "clips_count": len(clips),
                            "clips": clips
                        })
                    except Exception:
                        pass
    return history


class PublishClipRequest(BaseModel):
    video_id: str
    filename: str
    title: str = "Corte Viral"
    hashtags: List[str] = []
    delete_after: bool = False


@app.post("/api/clips/publish")
def publish_single_clip(req: PublishClipRequest):
    """Permite postar (ou tentar repostar) um clipe já salvo no disco diretamente pelo painel."""
    try:
        v_path = safe_media_path(OUTPUT_DIR, req.video_id, req.filename)
    except ValueError as e:
        log_event(f"🛡️ [PATH TRAVERSAL BLOQUEADO] {e}")
        raise HTTPException(status_code=400, detail=str(e))

    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado no disco.")

    log_event(f"📲 Postando manualmente {req.filename} ({req.video_id}) no TikTok...")
    res = publish_clip_to_tiktok(
        video_path=str(v_path),
        title=req.title,
        hashtags=req.hashtags,
        delete_after_post=req.delete_after
    )

    # Atualiza postagens.json se existir
    meta_file = OUTPUT_DIR / req.video_id / "postagens.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                clips = json.load(f)
            for c in clips:
                fname = c.get("filename") or f"corte_{c.get('clip_number', 1):02d}.mp4"
                if fname == req.filename:
                    c["auto_post_status"] = res
                    c["file_exists"] = v_path.exists()
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(clips, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    if res.get("success"):
        log_event(f"✅ {req.filename} publicado com sucesso no TikTok!")
    else:
        log_event(f"⚠️ Falha ao publicar {req.filename}: {res.get('error')}")
    return res

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
    try:
        updated = {
            "GEMINI_API_KEY": sanitize_env_value(cfg.gemini_key),
            "TIKTOK_ACCESS_TOKEN": sanitize_env_value(cfg.tiktok_token),
            "TIKTOK_PRIVACY_LEVEL": validate_privacy(cfg.privacy),
            "WHISPER_MODEL": validate_whisper_model(cfg.whisper_model)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    env_file = BASE_DIR / ".env"
    lines = []
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

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
def serve_media(video_id: str, filename: str, download: int = 0):
    try:
        file_path = safe_media_path(OUTPUT_DIR, video_id, filename)
    except ValueError as e:
        log_event(f"🛡️ [PATH TRAVERSAL BLOQUEADO] {e}")
        raise HTTPException(status_code=400, detail="Acesso negado.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    media_type = "video/mp4" if filename.endswith(".mp4") else "image/jpeg"
    if download:
        safe_dl_name = f"{video_id}_{filename}"
        return FileResponse(
            file_path,
            media_type=media_type,
            filename=safe_dl_name,
            headers={"Content-Disposition": f'attachment; filename="{safe_dl_name}"'}
        )
    return FileResponse(file_path, media_type=media_type)

@app.get("/api/qr")
def local_qr_code():
    """Gera o QR Code de acesso mobile 100% localmente em SVG (sem enviar IP a servidores externos)."""
    ip = get_local_ip()
    mobile_url = f"http://{ip}:{SERVER_PORT}"
    try:
        import segno
        qr = segno.make(mobile_url, error="m")
        buf = io.BytesIO()
        qr.save(buf, kind="svg", scale=5, border=2, dark="#0b0d11", light="#ffffff")
        return Response(content=buf.getvalue(), media_type="image/svg+xml")
    except Exception:
        fallback_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180">'
            '<rect width="100%" height="100%" fill="#ffffff"/>'
            '<text x="50%" y="50%" text-anchor="middle" fill="#0b0d11" font-size="12">Use o link abaixo</text>'
            '</svg>'
        )
        return Response(content=fallback_svg, media_type="image/svg+xml")


class CookieConsentRequest(BaseModel):
    preferences: bool = False


class LgpdFormRequest(BaseModel):
    request_type: str = "duvida"
    contact_email: str = ""
    details: str = ""


@app.get("/api/legal/documents")
def legal_documents():
    """Retorna Política de Privacidade, Termos de Uso, Política de Reembolso, Cookies, Leis Brasileiras e Dados Legais."""
    return get_legal_documents()


@app.get("/api/lgpd/consent")
def lgpd_get_consent():
    return get_cookie_consent()


@app.post("/api/lgpd/consent")
def lgpd_save_consent(req: CookieConsentRequest):
    rec = save_cookie_consent(preferences=req.preferences)
    log_event(f"⚖️ Preferências de cookies/LGPD atualizadas (preferências opcionais: {rec['preferences']}).")
    return rec


@app.get("/api/lgpd/export-data")
def lgpd_export_data():
    """Art. 18, II e V da LGPD — Exportação / Portabilidade dos dados do titular em JSON."""
    payload = export_user_data()
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=raw,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="meus_dados_lgpd_clip_farm.json"'}
    )


@app.post("/api/lgpd/delete-all-data")
def lgpd_delete_all():
    """Art. 18, VI da LGPD — Exclusão definitiva de sessões, cookies, vídeos, histórico e logs locais."""
    res = delete_all_user_data(system_logs_deque=SYSTEM_LOGS)
    JOBS.clear()
    return res


@app.post("/api/lgpd/request")
def lgpd_submit_request(req: LgpdFormRequest):
    """Formulário LGPD de coleta mínima para exercer direitos do titular (Art. 18)."""
    try:
        entry = submit_lgpd_request(
            request_type=req.request_type,
            contact_email=req.contact_email,
            details=req.details
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    log_event(f"⚖️ Solicitação LGPD registrada com protocolo {entry['protocol']} ({entry['type']}).")
    return {"success": True, "protocol": entry["protocol"], "entry": entry}


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
