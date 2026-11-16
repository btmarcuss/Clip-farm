import shutil
from pathlib import Path

def get_ffmpeg_exe() -> str:
    """
    Retorna o executável do FFmpeg disponível no sistema.
    Primeiro verifica se 'ffmpeg' já existe no PATH global.
    Caso não exista, busca o binário embutido do imageio-ffmpeg.
    """
    cmd = shutil.which("ffmpeg")
    if cmd:
        return cmd
    
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"
