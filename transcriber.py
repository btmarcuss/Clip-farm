import os
from faster_whisper import WhisperModel
from config import WHISPER_MODEL

# Cache do modelo Whisper — carregado uma única vez na memória ao iniciar o servidor.
_WHISPER_CACHE: dict = {}


def get_cached_model(size: str) -> WhisperModel:
    if size not in _WHISPER_CACHE:
        print(f"🔄 Carregando modelo Whisper '{size}' na memória (int8/CPU otimizado)...")
        threads = os.cpu_count() or 4
        try:
            _WHISPER_CACHE[size] = WhisperModel(
                size,
                device="auto",
                compute_type="int8",
                cpu_threads=threads,
            )
        except Exception:
            _WHISPER_CACHE[size] = WhisperModel(size, device="auto", compute_type="auto", cpu_threads=threads)
        print(f"✅ Modelo Whisper '{size}' pronto e cacheado ({threads} threads).")
    return _WHISPER_CACHE[size]


def transcribe_audio(audio_path: str, model_size: str = None) -> list:
    """
    Transcreve o arquivo de áudio gerando segmentos e timestamps detalhados por palavra.
    Usa VAD (Voice Activity Detection), int8 e beam_size=1 para máxima velocidade na CPU.
    """
    size = model_size or os.getenv("WHISPER_MODEL", WHISPER_MODEL) or "base"
    print(f"[2/4] 🎙️ Transcrevendo com Faster-Whisper (modelo: {size}, beam_size=1, word_timestamps=True)...")

    model = get_cached_model(size)
    segments, info = model.transcribe(
        audio_path,
        language="pt",
        beam_size=1,
        best_of=1,
        condition_on_previous_text=False,
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
