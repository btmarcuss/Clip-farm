import json
import math
import re
import time
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, MIN_CLIP_DURATION, MAX_CLIP_DURATION

# Limite absoluto de segurança por job para não explodir tempo/disco
ABSOLUTE_MAX_CLIPS = 100
# Quantidade segura de cortes pedidos por chamada à IA (evita truncamento de JSON)
MAX_CLIPS_PER_CHUNK = 12
# Tamanho máximo de texto por bloco enviado ao Gemini (~10-15 min de fala)
MAX_CHARS_PER_CHUNK = 22000


def _call_gemini_json(client: genai.Client, prompt: str) -> list:
    """Chama o Gemini com fallback automático entre modelos e retorno JSON estrito."""
    models = [
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-2.5-flash-lite",
    ]

    last_error = None
    raw_text = ""
    for model_name in models:
        for attempt in range(2):
            try:
                print(f"🧠 Chamando {model_name} (tentativa {attempt + 1}/2)...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                print(f"✅ Modelo {model_name} respondeu com sucesso!")
                raw_text = (response.text or "").strip()
                break
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    wait = (attempt + 1) * 4
                    print(f"⚠️ Modelo {model_name} ocupado. Aguardando {wait}s...")
                    time.sleep(wait)
                elif "404" in err_str or "NOT_FOUND" in err_str:
                    print(f"⚠️ Modelo {model_name} indisponível. Tentando próximo...")
                    break
                else:
                    raise
        else:
            continue
        if raw_text:
            break
    else:
        raise RuntimeError(f"Nenhum modelo Gemini disponível. Último erro: {last_error}")

    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    parsed = json.loads(cleaned)
    if isinstance(parsed, dict) and "clips" in parsed:
        parsed = parsed["clips"]
    return parsed if isinstance(parsed, list) else []


def _split_transcript_into_chunks(transcript_segments: list, max_chars: int = MAX_CHARS_PER_CHUNK, max_seconds: float = 720.0) -> list:
    """
    Divide a transcrição em blocos cronológicos contínuos (~12 min ou 22k chars cada)
    para cobrir 100% do vídeo sem cortar o final.
    """
    chunks = []
    current_lines = []
    current_chars = 0
    chunk_start = None

    for seg in transcript_segments:
        line = f"[{seg['start']}s -> {seg['end']}s] {seg['text']}"
        if chunk_start is None:
            chunk_start = seg["start"]

        seg_elapsed = seg["end"] - chunk_start
        if current_lines and (current_chars + len(line) > max_chars or seg_elapsed > max_seconds):
            chunks.append({
                "start": chunk_start,
                "end": seg["start"],
                "text": "\n".join(current_lines)
            })
            current_lines = []
            current_chars = 0
            chunk_start = seg["start"]

        current_lines.append(line)
        current_chars += len(line) + 1

    if current_lines:
        chunks.append({
            "start": chunk_start or 0.0,
            "end": transcript_segments[-1]["end"],
            "text": "\n".join(current_lines)
        })

    return chunks


def _deduplicate_and_validate_clips(clips: list, video_end: float) -> list:
    """Valida timestamps, corrige durações e remove cortes sobrepostos (>40% overlap)."""
    valid = []
    for c in clips:
        try:
            st = max(0.0, float(c.get("start_time", 0)))
            en = min(video_end, float(c.get("end_time", 0)))
            dur = en - st
            if dur < 10.0:
                continue
            if dur > MAX_CLIP_DURATION + 15:
                en = st + MAX_CLIP_DURATION
            c["start_time"] = round(st, 2)
            c["end_time"] = round(en, 2)
            c.setdefault("suggested_title", "Corte Viral")
            c.setdefault("hook_phrase", "")
            c.setdefault("reason", "Momento de alta retenção")
            c.setdefault("hashtags", ["#cortes", "#viral", "#foryou"])
            valid.append(c)
        except Exception:
            continue

    # Ordena cronologicamente e remove sobreposições excessivas
    valid.sort(key=lambda x: x["start_time"])
    deduped = []
    for c in valid:
        is_overlap = False
        c_dur = max(1.0, c["end_time"] - c["start_time"])
        for kept in deduped:
            inter_start = max(c["start_time"], kept["start_time"])
            inter_end = min(c["end_time"], kept["end_time"])
            overlap = max(0.0, inter_end - inter_start)
            if overlap / c_dur > 0.4:
                is_overlap = True
                break
        if not is_overlap:
            deduped.append(c)

    return deduped


def find_viral_moments(transcript_segments: list, max_clips: int = 3, audio_spikes: list = None, api_key: str = None) -> list:
    """
    Analisa 100% da transcrição (em blocos se necessário) e os picos de áudio com o Gemini
    para extrair cortes virais.
    - max_clips == 0 ativa o MODO MÁXIMO POSSÍVEL: calcula quantos cortes cabem no vídeo inteiro
      (sem sobreposição) e extrai todos os momentos aproveitáveis do início ao fim.
    - max_clips > 0 extrai até a quantidade desejada (até 100 cortes).
    """
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("Chave GEMINI_API_KEY não configurada! Adicione no arquivo .env ou passe como parâmetro.")

    if not transcript_segments:
        raise ValueError("Transcrição vazia — não há falas suficientes para gerar cortes.")

    video_start = transcript_segments[0]["start"]
    video_end = transcript_segments[-1]["end"]
    total_duration = max(1.0, video_end - video_start)

    max_mode = (int(max_clips) <= 0)
    if max_mode:
        # Calcula o máximo realista sem sobreposição (~1 corte a cada MIN_CLIP_DURATION + 10s)
        avg_slot = max(25.0, float(MIN_CLIP_DURATION) + 10.0)
        target_clips = max(1, min(ABSOLUTE_MAX_CLIPS, int(total_duration // avg_slot)))
        print(f"[3/4] 🔥 MODO MÁXIMO POSSÍVEL ativado! Duração: {int(total_duration)}s -> buscando até {target_clips} cortes em todo o vídeo...")
    else:
        target_clips = max(1, min(ABSOLUTE_MAX_CLIPS, int(max_clips)))
        print(f"[3/4] 🧠 Analisando todo o vídeo com IA Gemini para selecionar até {target_clips} cortes virais...")

    chunks = _split_transcript_into_chunks(transcript_segments)
    client = genai.Client(api_key=key)

    all_clips = []
    total_chunks = len(chunks)

    # Distribui a meta de cortes proporcionalmente pela duração de cada bloco
    for idx, chunk in enumerate(chunks, 1):
        chunk_dur = max(1.0, chunk["end"] - chunk["start"])
        if max_mode:
            avg_slot = max(25.0, float(MIN_CLIP_DURATION) + 10.0)
            chunk_quota = max(1, min(MAX_CLIPS_PER_CHUNK, int(math.ceil(chunk_dur / avg_slot))))
        else:
            prop = chunk_dur / total_duration
            chunk_quota = max(1, min(MAX_CLIPS_PER_CHUNK, int(math.ceil(target_clips * prop))))

        # Filtra apenas os picos sonoros que pertencem a este bloco
        chunk_spikes = []
        if audio_spikes:
            chunk_spikes = [sp for sp in audio_spikes if chunk["start"] <= sp["timestamp"] <= chunk["end"]]

        spikes_info = ""
        if chunk_spikes:
            spikes_info = (
                "\n[Picos de Volume e Reações neste trecho]: "
                + ", ".join([f"{sp['timestamp']}s" for sp in chunk_spikes[:25]])
                + "\n"
            )

        extra_instruction = (
            "MODO EXTRAÇÃO MÁXIMA: extraia o MAIOR número possível de cortes distintos, não sobrepostos e completos que cubram todo este bloco de vídeo."
            if max_mode
            else f"Selecione os {chunk_quota} melhores momentos distintos e não sobrepostos deste trecho."
        )

        prompt = f"""
Você é um estrategista e editor sênior de conteúdo viral para TikTok, Instagram Reels e YouTube Shorts.
Analise o bloco {idx}/{total_chunks} da transcrição ({round(chunk['start'], 1)}s até {round(chunk['end'], 1)}s) e identifique até {chunk_quota} cortes de alta retenção.
{extra_instruction}
{spikes_info}

Critérios inegociáveis:
1. DURAÇÃO: Cada clipe deve ter entre {MIN_CLIP_DURATION} e {MAX_CLIP_DURATION} segundos (end_time - start_time).
2. SEM SOBREPOSIÇÃO: Os cortes NÃO podem repetir o mesmo intervalo de tempo (start_time de um corte deve ser maior ou igual ao end_time do anterior).
3. GANCHO (HOOK): Os primeiros 3 segundos precisam prender a atenção.
4. FLUXO NATURAL: Comece e termine em pausas naturais das frases, usando apenas timestamps que existam nesta transcrição.
5. TÍTULOS E TAGS: Título magnético curto para TikTok e 5 hashtags relevantes.

Transcrição do bloco {idx}/{total_chunks}:
{chunk['text']}

Retorne ESTRITAMENTE uma lista JSON válida:
[
  {{
    "start_time": 120.5,
    "end_time": 172.0,
    "hook_phrase": "Frase de abertura dos primeiros 3 segundos",
    "reason": "Motivo da viralidade",
    "suggested_title": "Título magnético para o TikTok",
    "hashtags": ["#cortes", "#viral", "#foryou", "#reels", "#shorts"]
  }}
]
"""

        print(f"📦 Analisando bloco {idx}/{total_chunks} ({int(chunk['start'])}s–{int(chunk['end'])}s) -> meta: até {chunk_quota} cortes...")
        try:
            chunk_clips = _call_gemini_json(client, prompt)
            all_clips.extend(chunk_clips)
        except Exception as e:
            print(f"⚠️ Erro no bloco {idx}/{total_chunks}: {e}")
            if total_chunks == 1:
                raise

        if not max_mode and len(all_clips) >= target_clips + 4:
            # Já tem margem suficiente se tiver muitos blocos
            pass

    final_clips = _deduplicate_and_validate_clips(all_clips, video_end=video_end)

    if not final_clips:
        raise RuntimeError("A IA não conseguiu extrair cortes válidos deste vídeo.")

    # Se não estiver em modo máximo, limita à quantidade exata solicitada
    if not max_mode and len(final_clips) > target_clips:
        final_clips = final_clips[:target_clips]
    elif len(final_clips) > ABSOLUTE_MAX_CLIPS:
        final_clips = final_clips[:ABSOLUTE_MAX_CLIPS]

    print(f"🎯 IA selecionou {len(final_clips)} cortes virais únicos cobrindo o vídeo!")
    return final_clips
