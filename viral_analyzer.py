import json
import re
from google import genai
from config import GEMINI_API_KEY, MIN_CLIP_DURATION, MAX_CLIP_DURATION

def find_viral_moments(transcript_segments: list, max_clips: int = 3, audio_spikes: list = None, api_key: str = None) -> list:
    """
    Submete a transcrição com marcações de tempo e os picos de áudio ao Gemini
    para identificar os trechos de maior retenção, surpresa, polêmica, humor e viralidade.
    """
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("Chave GEMINI_API_KEY não configurada! Adicione no arquivo .env ou passe como parâmetro.")

    print(f"[3/4] 🧠 Analisando retenção, ganchos e momentos virais com IA Gemini...")

    formatted_transcript = "\n".join(
        [f"[{s['start']}s -> {s['end']}s] {s['text']}" for s in transcript_segments]
    )

    spikes_info = ""
    if audio_spikes:
        spikes_info = f"\n[Picos de Volume e Reações Detectados no Áudio]: " + ", ".join(
            [f"{sp['timestamp']}s" for sp in audio_spikes]
        ) + "\n(Dica: Esses picos sonoros costumam coincidir com risadas altas, sustos ou discussões acaloradas)\n"

    prompt = f"""
Você é um estrategista e editor sênior de conteúdo viral para redes como TikTok, Instagram Reels e YouTube Shorts.
Analise a transcrição com timestamps abaixo e identifique os {max_clips} momentos com MAIOR probabilidade de viralização.
{spikes_info}

Critérios inegociáveis:
1. DURAÇÃO: Cada clipe deve ter entre {MIN_CLIP_DURATION} e {MAX_CLIP_DURATION} segundos (end_time - start_time).
2. GANCHO (HOOK): Os primeiros 3 segundos do corte precisam ser irresistíveis: uma frase polêmica, uma pergunta curiosa, uma reação forte ou o início de uma história instigante.
3. FLUXO NATURAL: Não corte no meio de frases; comece e termine nas pausas naturais dos pensamentos.
4. TÍTULOS E TAGS: Gere um título no formato TikTok (curto, intrigante) e 5 hashtags relevantes.

Transcrição do conteúdo:
{formatted_transcript[:55000]}

Retorne ESTRITAMENTE uma lista JSON válida, sem blocos de texto explicativos fora do JSON:
[
  {{
    "start_time": 120.5,
    "end_time": 172.0,
    "hook_phrase": "Frase de abertura dos primeiros 3 segundos",
    "reason": "Motivo da viralidade (ex: quebra de expectativa, humor, polêmica)",
    "suggested_title": "Título magnético para o TikTok",
    "hashtags": ["#cortes", "#viral", "#foryou", "#podcast", "#reflexao"]
  }}
]
"""

    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )

    raw_text = response.text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        clips_data = json.loads(cleaned)
    except Exception as e:
        print(f"⚠️ Erro ao parsear resposta da IA: {e}\nResposta bruta: {raw_text}")
        raise

    print(f"🎯 IA selecionou {len(clips_data)} cortes virais!")
    return clips_data
