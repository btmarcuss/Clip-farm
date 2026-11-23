import subprocess
import re
from ffmpeg_helper import get_ffmpeg_exe


def detect_audio_spikes(audio_path: str, top_n: int = 60) -> list:
    """
    Analisa o áudio usando FFmpeg silencedetect para identificar momentos de
    energia sonora (retomadas após pausa, gritos, risadas ou reações) distribuídos
    ao longo de TODO o vídeo — não apenas no início.
    """
    print("🔊 Analisando picos de energia sonora e reações em todo o áudio...")

    ffmpeg_bin = get_ffmpeg_exe()
    cmd = [
        ffmpeg_bin, "-i", str(audio_path),
        "-af", "silencedetect=noise=-30dB:d=0.5",
        "-f", "null", "-"
    ]

    result = subprocess.run(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    starts = [float(m) for m in re.findall(r"silence_end: ([\d\.]+)", result.stderr)]
    if not starts:
        return []

    # Amostragem uniforme ao longo de todo o vídeo para cobrir do início ao fim
    if len(starts) > top_n:
        step = len(starts) / top_n
        selected = [starts[int(i * step)] for i in range(top_n)]
    else:
        selected = starts

    spikes = []
    for s in selected:
        spikes.append({
            "timestamp": round(s, 2),
            "estimated_highlight_window": (max(0.0, round(s - 5, 2)), round(s + 35, 2))
        })

    return spikes
