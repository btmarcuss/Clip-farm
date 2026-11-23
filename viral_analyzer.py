import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, MIN_CLIP_DURATION, MAX_CLIP_DURATION

# Limite absoluto de segurança por job para não explodir tempo/disco
ABSOLUTE_MAX_CLIPS = 100
# Quantidade segura de cortes pedidos por chamada à IA (evita truncamento de JSON)
MAX_CLIPS_PER_CHUNK = 12
# Tamanho máximo de texto por bloco enviado ao Gemini (~10-15 min de fala)
MAX_CHARS_PER_CHUNK = 22000


def _parse_gemini_json_resilient(raw_text: str) -> list:
    """Faz parse resiliente da resposta JSON do Gemini (remove markdown, trailing commas e texto extra)."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", (raw_text or "").strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    # Tenta parse direto primeiro
    for candidate in (cleaned, re.sub(r",\s*([\]}])", r"\1", cleaned)):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "clips" in parsed:
                parsed = parsed["clips"]
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

    # Fallback: extrai apenas o bloco de array [...]
    match = re.search(r"\[[\s\S]*\]", cleaned)
    if match:
        snippet = re.sub(r",\s*([\]}])", r"\1", match.group(0))
        parsed = json.loads(snippet)
        if isinstance(parsed, list):
            return parsed

    raise ValueError("Resposta JSON inválida da IA")


def _call_gemini_json(client: genai.Client, prompt: str) -> list:
    """
    Chama o Gemini priorizando os modelos Flash-Lite (muito mais rápidos e estáveis),
    trocando rapidamente de modelo em caso de 503 para nunca travar o pipeline.
    """
    models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
    ]

    last_error = None
    for model_name in models:
        try:
            print(f"🧠 Chamando {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    http_options=types.HttpOptions(timeout=25000),
                )
            )
            raw_text = (response.text or "").strip()
            parsed = _parse_gemini_json_resilient(raw_text)
            if parsed:
                print(f"✅ Modelo {model_name} respondeu com JSON válido ({len(parsed)} itens)!")
                return parsed
        except Exception as e:
            last_error = e
            err_str = str(e)
            print(f"⚠️ {model_name} indisponível/lento ({err_str[:80]}). Pulando imediatamente p/ próximo...")
            continue

    raise RuntimeError(f"Todos os modelos Gemini indisponíveis no momento. Último erro: {last_error}")


def _local_smart_fallback_clips(transcript_segments: list, target_clips: int, audio_spikes: list = None) -> list:
    """
    Fallback instantâneo (0.01s) caso toda a API do Gemini esteja sofrendo pico 503 simultâneo:
    seleciona janelas de fala completas alinhadas aos picos de energia sonora distribuídos pelo vídeo.
    """
    if not transcript_segments:
        return []
    video_start = transcript_segments[0]["start"]
    video_end = transcript_segments[-1]["end"]
    total_dur = max(1.0, video_end - video_start)
    clip_len = min(max(MIN_CLIP_DURATION + 12, 35), MAX_CLIP_DURATION)

    # Cria âncoras distribuídas ao longo do vídeo (priorizando picos de áudio se existirem)
    anchors = []
    if audio_spikes:
        anchors = [sp["timestamp"] for sp in audio_spikes]
    if len(anchors) < target_clips:
        step = total_dur / max(target_clips, 1)
        anchors = [video_start + i * step for i in range(target_clips)]

    clips = []
    used_until = -1.0
    for idx, anchor in enumerate(anchors):
        if len(clips) >= target_clips:
            break
        # Encontra o segmento de fala mais próximo da âncora que não sobreponha o corte anterior
        start_seg = next((s for s in transcript_segments if s["start"] >= max(anchor - 4.0, used_until + 1.0)), None)
        if not start_seg:
            continue
        st = start_seg["start"]
        # Fecha o corte no final de um segmento natural dentro de [MIN_CLIP_DURATION, MAX_CLIP_DURATION]
        end_seg = None
        for s in transcript_segments:
            d = s["end"] - st
            if d >= MIN_CLIP_DURATION:
                end_seg = s
                if d >= clip_len:
                    break
        en = end_seg["end"] if end_seg else min(video_end, st + clip_len)
        if en - st < 15.0:
            continue
        used_until = en
        snippet_text = start_seg["text"].strip()[:75]
        clips.append({
            "start_time": round(st, 2),
            "end_time": round(en, 2),
            "hook_phrase": snippet_text,
            "reason": "Seleção automática baseada em pico de energia sonora e ritmo de fala",
            "suggested_title": snippet_text if len(snippet_text) > 12 else f"Corte #{len(clips)+1}",
            "hashtags": ["#cortes", "#clips", "#foryou", "#reels", "#shorts"],
        })
    return clips


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

    def _analyze_chunk(idx: int, chunk: dict) -> list:
        chunk_dur = max(1.0, chunk["end"] - chunk["start"])
        if max_mode:
            avg_slot = max(25.0, float(MIN_CLIP_DURATION) + 10.0)
            chunk_quota = max(1, min(MAX_CLIPS_PER_CHUNK, int(math.ceil(chunk_dur / avg_slot))))
        else:
            prop = chunk_dur / total_duration
            chunk_quota = max(1, min(MAX_CLIPS_PER_CHUNK, int(math.ceil(target_clips * prop))))

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
Você é um estrategista e editor sênior de conteúdo curto para TikTok, Instagram Reels e YouTube Shorts.
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
    "reason": "Motivo da seleção",
    "suggested_title": "Título curto para o TikTok",
    "hashtags": ["#cortes", "#clips", "#foryou", "#reels", "#shorts"]
  }}
]
"""

        print(f"📦 Analisando bloco {idx}/{total_chunks} ({int(chunk['start'])}s–{int(chunk['end'])}s) -> meta: até {chunk_quota} cortes...")
        return _call_gemini_json(client, prompt)

    if total_chunks == 1:
        try:
            all_clips.extend(_analyze_chunk(1, chunks[0]))
        except Exception as e:
            print(f"⚠️ API Gemini indisponível ({e}); ativando seleção inteligente local por picos de áudio!")
    else:
        # Paraleliza análise de blocos em vídeos longos (até 4 chamadas simultâneas)
        with ThreadPoolExecutor(max_workers=min(total_chunks, 4)) as pool:
            futs = {pool.submit(_analyze_chunk, idx, ch): idx for idx, ch in enumerate(chunks, 1)}
            for fut in as_completed(futs):
                idx = futs[fut]
                try:
                    all_clips.extend(fut.result())
                except Exception as e:
                    print(f"⚠️ Erro no bloco {idx}/{total_chunks}: {e}")

    final_clips = _deduplicate_and_validate_clips(all_clips, video_end=video_end)

    if not final_clips:
        print("⚡ Aplicando fallback local por picos sonoros e pausas de fala para manter o pipeline ativo...")
        final_clips = _local_smart_fallback_clips(transcript_segments, target_clips, audio_spikes)

    if not final_clips:
        raise RuntimeError("Não foi possível extrair cortes válidos deste vídeo.")

    # Se não estiver em modo máximo, limita à quantidade exata solicitada
    if not max_mode and len(final_clips) > target_clips:
        final_clips = final_clips[:target_clips]
    elif len(final_clips) > ABSOLUTE_MAX_CLIPS:
        final_clips = final_clips[:ABSOLUTE_MAX_CLIPS]

    print(f"🎯 IA selecionou {len(final_clips)} cortes virais únicos cobrindo o vídeo!")
    return final_clips
