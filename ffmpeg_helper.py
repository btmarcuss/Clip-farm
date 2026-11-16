import os
import shutil
from pathlib import Path

def get_ffmpeg_exe() -> str:
    """
    Retorna o caminho absoluto do executável FFmpeg.
    Garante que exista um binário nomeado 'ffmpeg.exe' e adiciona
    o diretório correspondente ao PATH do sistema operacional.
    """
    # 1. Verifica se já existe um 'ffmpeg.exe' no PATH
    cmd = shutil.which("ffmpeg")
    if cmd and Path(cmd).exists():
        return cmd

    # 2. Verifica se existe ffmpeg.exe na pasta local do projeto
    local_ffmpeg = Path(__file__).resolve().parent / "ffmpeg.exe"
    if local_ffmpeg.exists():
        bin_dir = str(local_ffmpeg.parent)
        if bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        return str(local_ffmpeg)

    # 3. Utiliza o pacote imageio_ffmpeg
    try:
        import imageio_ffmpeg
        orig_exe = imageio_ffmpeg.get_ffmpeg_exe()
        bin_dir = Path(orig_exe).parent
        standard_ffmpeg = bin_dir / "ffmpeg.exe"

        # Se o executável do imageio_ffmpeg tiver sufixo de versão, cria a cópia padrão 'ffmpeg.exe'
        if not standard_ffmpeg.exists():
            try:
                shutil.copyfile(orig_exe, standard_ffmpeg)
            except Exception:
                pass

        final_exe = str(standard_ffmpeg if standard_ffmpeg.exists() else orig_exe)
        
        # Adiciona ao PATH do processo para que o yt-dlp e subprocessos o encontrem sempre
        if str(bin_dir) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")

        return final_exe
    except Exception:
        return "ffmpeg"
