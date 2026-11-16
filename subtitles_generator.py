from pathlib import Path
import math

def format_ass_time(seconds: float) -> str:
    """Converte segundos para o formato de tempo do ASS: H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(math.floor((seconds - int(seconds)) * 100))
    return f"{hrs:01d}:{mins:02d}:{secs:02d}.{centis:02d}"

def generate_tiktok_ass_subtitles(
    segments_with_words: list,
    clip_start: float,
    clip_end: float,
    output_ass_path: str,
    max_words_per_line: int = 3
) -> str:
    """
    Gera um arquivo de legenda no formato .ASS (Advanced SubStation Alpha)
    com estilo dinâmico de alto impacto visual (Estilo TikTok / Alex Hormozi):
    - Fonte em caixa alta (uppercase), negrito, borda preta grossa.
    - Centralizada verticalmente ligeiramente abaixo do meio (MarginV=450).
    - Palavras agrupadas em blocos de 2 a 3 palavras para retenção máxima.
    """
    out_file = Path(output_ass_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokDefault,Arial,86,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,10,3,2,60,60,420,1
Style: TikTokHighlight,Arial,90,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,12,4,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    
    # Coleta todas as palavras que caem dentro da janela do clipe
    words_in_clip = []
    for seg in segments_with_words:
        # Se o segmento tem 'words', usamos palavra por palavra
        if "words" in seg and seg["words"]:
            for w in seg["words"]:
                if w["start"] >= clip_start and w["end"] <= clip_end:
                    words_in_clip.append({
                        "start": max(0.0, w["start"] - clip_start),
                        "end": max(0.0, w["end"] - clip_start),
                        "word": w["word"].strip().upper()
                    })
        else:
            # Fallback se não houver timestamps por palavra: usa o segmento ajustado
            if seg["start"] >= clip_start and seg["end"] <= clip_end:
                words_in_clip.append({
                    "start": max(0.0, seg["start"] - clip_start),
                    "end": max(0.0, seg["end"] - clip_start),
                    "word": seg["text"].strip().upper()
                })

    # Agrupa palavras em pedaços dinâmicos de leitura rápida (ex: 2 a 3 palavras)
    i = 0
    while i < len(words_in_clip):
        group = words_in_clip[i:i + max_words_per_line]
        if not group:
            break
        
        start_t = group[0]["start"]
        end_t = group[-1]["end"]
        # Garante duração mínima para não piscar rápido demais
        if end_t - start_t < 0.35:
            end_t = start_t + 0.35

        text_line = " ".join([item["word"] for item in group])
        
        start_str = format_ass_time(start_t)
        end_str = format_ass_time(end_t)
        
        # Alterna estilo para destacar impacto
        style = "TikTokHighlight" if any(len(item["word"]) > 6 for item in group) else "TikTokDefault"
        events.append(f"Dialogue: 0,{start_str},{end_str},{style},,0,0,0,,{text_line}")
        i += len(group)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    return str(out_file)
