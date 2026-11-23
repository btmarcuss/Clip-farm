import os
import subprocess
from pathlib import Path
import yt_dlp
from config import TEMP_DIR
from ffmpeg_helper import get_ffmpeg_exe

# Adiciona Node.js ao PATH para que o yt-dlp possa usar como JS runtime
_NODE_PATH = r"C:\Program Files\nodejs"
if _NODE_PATH not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _NODE_PATH + ";" + os.environ.get("PATH", "")

def download_youtube_video(url: str) -> dict:
    """
    Baixa o vídeo do YouTube em até 720p e extrai uma faixa de áudio WAV 16kHz mono.
    Suporta vídeos com streams separados (vídeo + áudio) usando FFmpeg para merge.
    """
    print(f"[1/4] 📥 Iniciando download: {url}")
    
    ffmpeg_bin = get_ffmpeg_exe()
    
    ydl_opts = {
        # Formato robusto: tenta mp4 720p + m4a, depois qualquer 720p, depois qualquer coisa
        # bestvideo+bestaudio garante merge mesmo quando streams são separados
        'format': (
            'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/'
            'bestvideo[height<=720]+bestaudio/'
            'bestvideo[height<=480]+bestaudio/'
            'best[height<=720]/'
            'best'
        ),
        'outtmpl': str(TEMP_DIR / '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'ffmpeg_location': ffmpeg_bin,
        'quiet': False,
        'no_warnings': True,
        # Múltiplas conexões para acelerar download
        'concurrent_fragment_downloads': 4,
        'retries': 3,
        'fragment_retries': 3,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id")
        video_title = info.get("title", "video")
        duration = info.get("duration", 0)
        
        # Localiza o arquivo de vídeo baixado
        video_path = TEMP_DIR / f"{video_id}.mp4"
        if not video_path.exists():
            for candidate in TEMP_DIR.glob(f"{video_id}.*"):
                if candidate.suffix.lower() in [".mp4", ".mkv", ".webm"]:
                    video_path = candidate
                    break

    print(f"🎬 Vídeo baixado: {video_path}")
    print(f"🎵 Extraindo áudio mono 16kHz para transcrição rápida...")
    
    audio_path = TEMP_DIR / f"{video_id}.wav"
    cmd_audio = [
        ffmpeg_bin, "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path)
    ]
    
    subprocess.run(cmd_audio, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return {
        "id": video_id,
        "title": video_title,
        "duration": duration,
        "video_path": str(video_path),
        "audio_path": str(audio_path)
    }
