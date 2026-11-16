from faster_whisper import WhisperModel
from config import WHISPER_MODEL

def transcribe_audio(audio_path: str, model_size: str = None) -> list:
    """
    Transcreve o arquivo de áudio gerando segmentos e timestamps detalhados por palavra.
    Usa VAD (Voice Activity Detection) para filtrar silêncios.
    """
    size = model_size or WHISPER_MODEL
    print(f"[2/4] 🎙️ Transcrevendo com Faster-Whisper (modelo: {size}, word_timestamps=True)...")
    
    # device="auto" seleciona cuda se disponível, senão cpu
    model = WhisperModel(size, device="auto", compute_type="auto")
    segments, info = model.transcribe(
        audio_path,
        language="pt",
        vad_filter=True,
        word_timestamps=True
    )
    
    transcript_segments = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            words_data = []
            if seg.words:
                for w in seg.words:
                    words_data.append({
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "word": w.word.strip(),
                        "probability": round(w.probability, 2)
                    })
            
            transcript_segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": text,
                "words": words_data
            })
            
    print(f"✅ Transcrição finalizada! Total de segmentos mapeados: {len(transcript_segments)}")
    return transcript_segments
