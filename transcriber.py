from faster_whisper import WhisperModel
from config import WHISPER_MODEL

def transcribe_audio(audio_path: str, model_size: str = None) -> list:
    """
    Transcreve o arquivo de áudio gerando segmentos com timestamps (segundos).
    Usa VAD (Voice Activity Detection) para filtrar silêncios.
    """
    size = model_size or WHISPER_MODEL
    print(f"[2/4] 🎙️ Transcrevendo com Faster-Whisper (modelo: {size})...")
    
    # device="auto" escolhe cuda se GPU estiver disponível, senão cpu
    model = WhisperModel(size, device="auto", compute_type="auto")
    segments, info = model.transcribe(audio_path, language="pt", vad_filter=True)
    
    transcript_segments = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            transcript_segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": text
            })
            
    print(f"✅ Transcrição finalizada! Total de trechos mapeados: {len(transcript_segments)}")
    return transcript_segments
