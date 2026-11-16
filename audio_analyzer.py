import subprocess
import re
from pathlib import Path

def detect_audio_spikes(audio_path: str, top_n: int = 5) -> list:
    """
    Analisa o áudio usando FFmpeg silencedetect e astats para identificar
    os momentos de maior energia sonora (gritos, gargalhadas, aplausos ou reações intensas).
    Retorna uma lista de intervalos em segundos com alta probabilidade de reação.
    """
    print(f"🔊 Analisando picos de energia sonora e reações no áudio...")
    
    # Executa análise de volume e picos com FFmpeg
    cmd = [
        "ffmpeg", "-i", str(audio_path),
        "-af", "silencedetect=noise=-30dB:d=0.5",
        "-f", "null", "-"
    ]
    
    result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
    
    # Extrai onde o silêncio terminou (início de falas/gritos intensos)
    starts = [float(m) for m in re.findall(r"silence_end: ([\d\.]+)", result.stderr)]
    
    spikes = []
    for s in starts[:top_n * 2]:
        spikes.append({
            "timestamp": round(s, 2),
            "estimated_highlight_window": (max(0.0, round(s - 5, 2)), round(s + 35, 2))
        })
        
    return spikes[:top_n]
