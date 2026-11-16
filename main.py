import argparse
import json
import os
from pathlib import Path
from config import OUTPUT_DIR, MAX_CLIPS, DEFAULT_LAYOUT, ENABLE_SUBTITLES, AUTO_POST
from downloader import download_youtube_video
from transcriber import transcribe_audio
from audio_analyzer import detect_audio_spikes
from viral_analyzer import find_viral_moments
from subtitles_generator import generate_tiktok_ass_subtitles
from video_editor import create_vertical_clip, generate_clip_thumbnail
from auto_publisher import publish_clip_to_tiktok

def process_video(
    url: str,
    num_clips: int = MAX_CLIPS,
    layout: str = DEFAULT_LAYOUT,
    use_subtitles: bool = ENABLE_SUBTITLES,
    auto_post: bool = AUTO_POST
):
    print("=" * 65)
    print("🚀 INICIANDO CLIP FARM AUTOMÁTICO (YouTube -> TikTok/Shorts)")
    if auto_post:
        print("📲 MODO AUTO-POST ATIVADO: Os cortes serão publicados no TikTok automaticamente!")
    print("=" * 65)

    # 1. Download do Vídeo e Extração de Áudio
    media = download_youtube_video(url)
    
    # 2. Picos de Volume / Reações Sonoras
    audio_spikes = detect_audio_spikes(media["audio_path"])
    
    # 3. Transcrição com Timestamps por Palavra
    transcript = transcribe_audio(media["audio_path"])
    
    # 4. Análise de Viralidade e Ganchos com IA
    viral_clips = find_viral_moments(transcript, max_clips=num_clips, audio_spikes=audio_spikes)
    
    # Pasta de saída exclusiva para o vídeo
    video_output_dir = OUTPUT_DIR / media["id"]
    video_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 5. Produção dos Clipes Verticais
    print(f"\n[4/4] ✂️ Renderizando {len(viral_clips)} cortes verticais (9:16)...")
    summary = []
    
    for idx, clip in enumerate(viral_clips, 1):
        clip_base_name = f"corte_{idx:02d}"
        video_out_path = video_output_dir / f"{clip_base_name}.mp4"
        thumb_out_path = video_output_dir / f"{clip_base_name}_thumb.jpg"
        sub_ass_path = None

        print(f"\n🔹 Processando Corte #{idx} ({clip['start_time']}s até {clip['end_time']}s)")
        print(f"   Hook: \"{clip.get('hook_phrase', 'N/A')}\"")
        print(f"   Título: {clip.get('suggested_title', '')}")
        print(f"   Tags: {' '.join(clip.get('hashtags', []))}")

        # Geração de Legendas Dinâmicas Estilo TikTok
        if use_subtitles:
            ass_file = video_output_dir / f"{clip_base_name}.ass"
            sub_ass_path = generate_tiktok_ass_subtitles(
                segments_with_words=transcript,
                clip_start=clip["start_time"],
                clip_end=clip["end_time"],
                output_ass_path=str(ass_file)
            )
            print(f"   📝 Legendas dinâmicas geradas: {ass_file.name}")

        # Renderização do Vídeo Vertical 9:16
        create_vertical_clip(
            video_path=media["video_path"],
            start_time=clip["start_time"],
            end_time=clip["end_time"],
            output_path=str(video_out_path),
            subtitles_ass_path=sub_ass_path,
            layout=layout
        )

        # Geração da Capa / Thumbnail do Vídeo
        generate_clip_thumbnail(
            video_path=str(video_out_path),
            timestamp=1.0,
            output_thumb_path=str(thumb_out_path)
        )

        # 6. Postagem Automática no TikTok (se ativado)
        post_status = None
        if auto_post:
            post_status = publish_clip_to_tiktok(
                video_path=str(video_out_path),
                title=clip.get("suggested_title", "Corte do Dia"),
                hashtags=clip.get("hashtags", [])
            )

        clip_data = {
            "clip_number": idx,
            "file": f"{clip_base_name}.mp4",
            "thumbnail": f"{clip_base_name}_thumb.jpg",
            "video_path": str(video_out_path),
            "start_time": clip["start_time"],
            "end_time": clip["end_time"],
            "duration": round(clip["end_time"] - clip["start_time"], 2),
            "suggested_title": clip.get("suggested_title", ""),
            "hook_phrase": clip.get("hook_phrase", ""),
            "reason": clip.get("reason", ""),
            "hashtags": clip.get("hashtags", []),
            "auto_post_status": post_status
        }
        summary.append(clip_data)

    # Salva relatório para postagem
    metadata_file = video_output_dir / "postagens.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 65)
    print(f"🎉 SUCESSO! Todos os cortes foram gerados!")
    print(f"📁 Pasta de Saída: {video_output_dir}")
    print(f"📄 Metadados de Postagem: {metadata_file}")
    if auto_post:
        print(f"📲 Postagem Automática finalizada para todos os cortes!")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automação Completa de Clip Farm (YouTube para TikTok/Shorts)")
    parser.add_argument("url", help="URL do vídeo ou live do YouTube")
    parser.add_argument("--clips", "-c", type=int, default=MAX_CLIPS, help=f"Quantidade de clipes (padrão: {MAX_CLIPS})")
    parser.add_argument("--layout", "-l", choices=["blur", "split"], default=DEFAULT_LAYOUT, help="Layout do vídeo: 'blur' ou 'split'")
    parser.add_argument("--no-subs", action="store_true", help="Desativa a queima de legendas animadas")
    parser.add_argument("--autopost", action="store_true", help="Publica automaticamente no TikTok após o corte")

    args = parser.parse_args()
    process_video(
        url=args.url,
        num_clips=args.clips,
        layout=args.layout,
        use_subtitles=not args.no_subs,
        auto_post=args.autopost or AUTO_POST
    )
