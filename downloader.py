import os
import json
import subprocess
import urllib.request
from pathlib import Path
import yt_dlp
from config import TEMP_DIR
from ffmpeg_helper import get_ffmpeg_exe

# Adiciona Node.js ao PATH para que o yt-dlp possa usar como JS runtime
_NODE_PATH = r"C:\Program Files\nodejs"
if _NODE_PATH not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _NODE_PATH + ";" + os.environ.get("PATH", "")

# Diretório local no SSD (%TEMP%) para evitar gargalo de leitura/escrita SMB na rede
_LOCAL_CACHE_DIR = Path(os.getenv("TEMP", str(TEMP_DIR))) / "clip_farm_cache"
_LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _extract_youtube_json3_transcript(info: dict) -> list:
    """
    Extrai legendas já prontas do YouTube (formato json3, com timestamps palavra por palavra)
    em ~0.3s, eliminando a necessidade de rodar Whisper na CPU na grande maioria dos vídeos!
    """
    subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    chosen_url = None
    chosen_lang = None
    # Prioridade: legendas manuais PT -> automáticas PT -> manuais EN -> automáticas EN
    for src in (subs, auto_subs):
        for lang in ("pt", "pt-BR", "pt-PT", "en"):
            if lang in src:
                for fmt in src[lang]:
                    if fmt.get("ext") == "json3" and fmt.get("url"):
                        chosen_url = fmt["url"]
                        chosen_lang = lang
                        break
            if chosen_url:
                break
        if chosen_url:
            break

    if not chosen_url:
        return []

    try:
        req = urllib.request.Request(
            chosen_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        events = data.get("events", [])
        segments = []
        for ev in events:
            t_start_ms = ev.get("tStartMs")
            d_dur_ms = ev.get("dDurationMs", 0)
            segs = ev.get("segs")
            if t_start_ms is None or not segs:
                continue

            ev_start = t_start_ms / 1000.0
            ev_end = (t_start_ms + max(d_dur_ms, 300)) / 1000.0

            raw_tokens = []
            for idx, s in enumerate(segs):
                token_txt = (s.get("utf8") or "").replace("\n", " ").strip()
                if not token_txt or token_txt == "[Música]" or token_txt == "[Music]":
                    continue
                offset_ms = s.get("tOffsetMs", 0)
                w_start = (t_start_ms + offset_ms) / 1000.0
                raw_tokens.append((w_start, token_txt))

            if not raw_tokens:
                continue

            words_data = []
            for i, (w_start, tok) in enumerate(raw_tokens):
                w_end = raw_tokens[i + 1][0] if i + 1 < len(raw_tokens) else ev_end
                if w_end <= w_start:
                    w_end = w_start + 0.25
                # Se um token tiver várias palavras (legendas manuais), divide proporcionalmente
                parts = tok.split()
                if len(parts) == 1:
                    words_data.append({
                        "start": round(w_start, 2),
                        "end": round(w_end, 2),
                        "word": parts[0],
                        "probability": 1.0,
                    })
                else:
                    step = (w_end - w_start) / len(parts)
                    for j, part in enumerate(parts):
                        words_data.append({
                            "start": round(w_start + j * step, 2),
                            "end": round(w_start + (j + 1) * step, 2),
                            "word": part,
                            "probability": 1.0,
                        })

            full_text = " ".join(w["word"] for w in words_data).strip()
            if full_text:
                segments.append({
                    "start": round(ev_start, 2),
                    "end": round(ev_end, 2),
                    "text": full_text,
                    "words": words_data,
                })

        if len(segments) >= 5:
            print(f"⚡ Transcrição instantânea obtida direto do YouTube ({chosen_lang}): {len(segments)} segmentos!")
            return segments
    except Exception as e:
        print(f"ℹ️ Legenda rápida do YouTube indisponível ({e}); usando Faster-Whisper local.")

    return []


def download_youtube_video(url: str) -> dict:
    """
    Baixa o vídeo em 720p (priorizando H.264 avc1 para decodificação 4x mais rápida que AV1)
    direto no SSD local (%TEMP%) para eliminar gargalos de rede SMB.
    Também tenta extrair a transcrição nativa do YouTube (json3) em ~0.3s;
    só gera o .wav 16kHz se precisar rodar o Whisper local.
    """
    print(f"[1/4] 📥 Iniciando download otimizado (720p H.264): {url}")

    ffmpeg_bin = get_ffmpeg_exe()

    ydl_opts = {
        # Prioriza 720p H.264 (avc1) que decodifica 3-5x mais rápido que AV1/VP9 no FFmpeg
        "format": (
            "bestvideo[height<=720][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=720]+bestaudio/"
            "best[height<=720]/"
            "best"
        ),
        "outtmpl": str(_LOCAL_CACHE_DIR / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "ffmpeg_location": ffmpeg_bin,
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 8,
        "retries": 3,
        "fragment_retries": 3,
        "writesubtitles": False,
        "writeautomaticsub": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id")
        video_title = info.get("title", "video")
        duration = info.get("duration", 0)

        video_path = _LOCAL_CACHE_DIR / f"{video_id}.mp4"
        if not video_path.exists():
            for candidate in _LOCAL_CACHE_DIR.glob(f"{video_id}.*"):
                if candidate.suffix.lower() in (".mp4", ".mkv", ".webm"):
                    video_path = candidate
                    break

    print(f"🎬 Vídeo 720p pronto no SSD local: {video_path.name}")

    # Tenta transcrição instantânea direto das legendas do YouTube (~0.3s!)
    yt_transcript = _extract_youtube_json3_transcript(info)

    # Só extrai WAV se NÃO houver transcrição do YouTube (economiza tempo e disco!)
    audio_path = str(video_path)
    if not yt_transcript:
        wav_path = _LOCAL_CACHE_DIR / f"{video_id}.wav"
        if not wav_path.exists() or wav_path.stat().st_size == 0:
            print("🎵 Extraindo áudio mono 16kHz para Faster-Whisper...")
            cmd_audio = [
                ffmpeg_bin, "-y",
                "-threads", "0",
                "-i", str(video_path),
                "-vn", "-sn", "-dn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                str(wav_path)
            ]
            subprocess.run(cmd_audio, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio_path = str(wav_path)

    return {
        "id": video_id,
        "title": video_title,
        "duration": duration,
        "video_path": str(video_path),
        "audio_path": audio_path,
        "youtube_transcript": yt_transcript,
    }
