import subprocess
from pathlib import Path
from ffmpeg_helper import get_ffmpeg_exe

def create_vertical_clip(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    subtitles_ass_path: str = None,
    layout: str = "blur"
) -> str:
    """
    Corta o trecho e converte para vertical 9:16 (1080x1920).
    - layout "blur": Fundo 1080x1920 desfocado com o vídeo original centralizado nítido.
    - layout "split": Divide a tela em duas metades (ideal para streamer em cima + jogo embaixo).
    - subtitles_ass_path: Caminho do arquivo .ass gerado para queimar legendas estilo TikTok.
    """
    duration = round(end_time - start_time, 2)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_exe()

    if layout == "split":
        video_filters = (
            "[0:v]crop=in_w/2:in_h:0:0,scale=1080:960[top];"
            "[0:v]crop=in_w/2:in_h:in_w/2:0,scale=1080:960[bottom];"
            "[top][bottom]vstack[vbase]"
        )
        base_label = "[vbase]"
    else:
        video_filters = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
            "[0:v]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[vbase]"
        )
        base_label = "[vbase]"

    if subtitles_ass_path and Path(subtitles_ass_path).exists():
        ass_path_escaped = str(Path(subtitles_ass_path).resolve()).replace("\\", "/").replace(":", "\\:")
        filter_complex = f"{video_filters};{base_label}subtitles='{ass_path_escaped}'[v]"
    else:
        filter_complex = f"{video_filters};{base_label}copy[v]"

    cmd = [
        ffmpeg_bin, "-y",
        "-ss", str(start_time),
        "-i", str(video_path),
        "-t", str(duration),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "ultrafast",   # ultrafast = 2-3x mais rápido que veryfast, qualidade ok para TikTok
        "-crf", "23",             # CRF 23 é imperceptível para mobile, arquivos menores
        "-tune", "fastdecode",    # Otimiza para decodificação rápida
        "-c:a", "aac",
        "-b:a", "128k",           # 128k suficiente para TikTok (era 192k)
        "-movflags", "+faststart", # Permite streaming progressivo (reprodução começa mais rápido)
        str(out_file)
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(out_file)

def generate_clip_thumbnail(video_path: str, timestamp: float, output_thumb_path: str):
    """
    Extrai um frame estático de alta resolução (1080x1920) para servir de capa/thumbnail do TikTok.
    """
    out_file = Path(output_thumb_path)
    ffmpeg_bin = get_ffmpeg_exe()
    cmd = [
        ffmpeg_bin, "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(out_file)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(out_file)
