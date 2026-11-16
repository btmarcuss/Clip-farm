import subprocess
from pathlib import Path

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

    if layout == "split":
        # Tela dividida: Metade de cima e metade de baixo
        video_filters = (
            "[0:v]crop=in_w/2:in_h:0:0,scale=1080:960[top];"
            "[0:v]crop=in_w/2:in_h:in_w/2:0,scale=1080:960[bottom];"
            "[top][bottom]vstack[vbase]"
        )
        base_label = "[vbase]"
    else:
        # Layout padrão "blur": fundo borrado + vídeo no centro
        video_filters = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
            "[0:v]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[vbase]"
        )
        base_label = "[vbase]"

    # Se tiver legenda ASS para queimar
    if subtitles_ass_path and Path(subtitles_ass_path).exists():
        # Formata o caminho do arquivo para o filtro do FFmpeg no Windows
        ass_path_escaped = str(Path(subtitles_ass_path).resolve()).replace("\\", "/").replace(":", "\\:")
        filter_complex = f"{video_filters};{base_label}subtitles='{ass_path_escaped}'[v]"
    else:
        filter_complex = f"{video_filters};{base_label}copy[v]"

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

def generate_clip_thumbnail(video_path: str, timestamp: float, output_thumb_path: str):
    """
    Extrai um frame estático de alta resolução (1080x1920) para servir de capa/thumbnail do TikTok.
    """
    out_file = Path(output_thumb_path)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(out_file)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(out_file)
