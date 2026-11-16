import subprocess
import re
from pathlib import Path
from ffmpeg_helper import get_ffmpeg_exe

def detect_audio_spikes(audio_path: str, top_n: int = 5) -> list:
    """
    Analisa o áudio usando FFmpeg silencedetect para identificar
    os momentos de maior energia sonora (gritos, gargalhadas, aplausos ou reações intensas).
    """
    print(f"🔊 Analisando picos de energia sonora e reações no áudio...")
    
    ffmpeg_bin = get_ffmpeg_exe()
    cmd = [
        ffmpeg_bin, "-i", str(audio_path),
        "-af", "silencedetect=noise=-30dB:d=0.5",
        "-f", "null", "-"
    ]
    
    result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
    
    starts = [float(m) for m in re.findall(r"silence_end: ([\d\.]+)", result.stderr)]
    
    spikes = []
    for s in starts[:top_n * 2]:
        spikes.append({
            "timestamp": round(s, 2),
            "estimated_highlight_window": (max(0.0, round(s - 5, 2)), round(s + 35, 2))
        })
        
    return spikes[:top_n]
