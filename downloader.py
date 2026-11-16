import os
import subprocess
from pathlib import Path
import yt_dlp
from config import TEMP_DIR
from ffmpeg_helper import get_ffmpeg_exe

def download_youtube_video(url: str) -> dict:
    """
    Baixa o vídeo do YouTube em até 1080p e extrai uma faixa de áudio WAV 16kHz mono
    para alimentar o pipeline de transcrição com eficiência.
    Garante a localização do FFmpeg para evitar erros de merge de formatos.
    """
    print(f"[1/4] 📥 Iniciando download: {url}")
    
    ffmpeg_bin = get_ffmpeg_exe()
    
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'outtmpl': str(TEMP_DIR / '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'ffmpeg_location': ffmpeg_bin,
        'quiet': False,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id")
        video_title = info.get("title", "video")
        duration = info.get("duration", 0)
        
        # Localiza o arquivo de vídeo baixado (pode ser .mp4 ou .mkv)
        video_path = TEMP_DIR / f"{video_id}.mp4"
        if not video_path.exists():
            # Procura por qualquer extensão baixada com esse ID
            for candidate in TEMP_DIR.glob(f"{video_id}.*"):
                if candidate.suffix.lower() in [".mp4", ".mkv", ".webm"]:
                    video_path = candidate
                    break

        audio_path = TEMP_DIR / f"{video_id}.wav"

    print(f"🎬 Vídeo baixado: {video_path}")
    print(f"🎵 Extraindo áudio mono 16kHz para transcrição rápida...")
    
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
