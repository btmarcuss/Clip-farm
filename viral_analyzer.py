import json
import re
from google import genai
from config import GEMINI_API_KEY, MIN_CLIP_DURATION, MAX_CLIP_DURATION

def find_viral_moments(transcript_segments: list, max_clips: int = 3, api_key: str = None) -> list:
    """
    Submete a transcrição com marcações de tempo ao Gemini para identificar
    os trechos de maior retenção, surpresa, polêmica, humor e viralidade.
    """
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("Chave GEMINI_API_KEY não configurada! Adicione no arquivo .env ou informe via parâmetro.")

    print(f"[3/4] 🧠 Analisando retenção e potencial viral com IA Gemini...")

    formatted_transcript = "\n".join(
        [f"[{s['start']}s -> {s['end']}s] {s['text']}" for s in transcript_segments]
    )

    prompt = f"""
Você é um editor de vídeos profissional e especialista em algoritmos de viralização do TikTok, Reels e YouTube Shorts.
Analise a transcrição com timestamps abaixo e extraia exatamente os {max_clips} melhores momentos com maior potencial de viralizar.

Critérios inegociáveis:
1. DURAÇÃO: Cada clipe deve ter entre {MIN_CLIP_DURATION} e {MAX_CLIP_DURATION} segundos (end_time - start_time).
2. GANCHO (HOOK): Os primeiros 3 segundos devem conter uma frase de impacto, mistério, choque, pergunta instigante ou início de uma história cativante.
3. FLUXO NATURAL: O corte deve começar e terminar no final de uma frase ou pensamento, sem cortar palavras pela metade.
4. TÍTULOS E TAGS: Crie um título altamente clicável (sem mentir) e 5 hashtags estratégicas.

Transcrição do conteúdo:
{formatted_transcript[:50000]}

Retorne ESTRITAMENTE uma lista JSON válida, sem blocos de texto antes ou depois:
[
  {{
    "start_time": 120.5,
    "end_time": 172.0,
    "hook_phrase": "Frase de abertura impactante nos primeiros 3s",
    "reason": "Explicação do porquê esse trecho tem alto potencial viral",
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
    # Remove eventuais formatações de markdown ```json ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        clips_data = json.loads(cleaned)
    except Exception as e:
        print(f"⚠️ Erro ao parsear resposta da IA: {e}\nResposta bruta: {raw_text}")
        raise

    print(f"🎯 IA selecionou {len(clips_data)} cortes virais!")
    return clips_data
