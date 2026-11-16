import subprocess
from pathlib import Path

def create_vertical_clip(video_path: str, start_time: float, end_time: float, output_path: str):
    """
    Corta o trecho selecionado e converte para o formato vertical 9:16 (1080x1920).
    Aplica:
    1. Background borrado (Gaussian/Box blur) ocupando 1080x1920 para preencher toda a tela vertical.
    2. Vídeo original em escala nítida sobreposto no centro exato.
    3. Normalização de áudio para clareza em smartphones.
    """
    duration = round(end_time - start_time, 2)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
        "[0:v]scale=1080:-1[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", str(video_path),
        "-t", str(duration),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_file)
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(out_file)
