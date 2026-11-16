import argparse
import json
import sys
from pathlib import Path
from config import OUTPUT_DIR, MAX_CLIPS
from downloader import download_youtube_video
from transcriber import transcribe_audio
from viral_analyzer import find_viral_moments
from video_editor import create_vertical_clip

def process_video(url: str, num_clips: int = MAX_CLIPS):
    print("=" * 60)
    print("🚀 INICIANDO CLIP FARM AUTOMÁTICO (YouTube -> TikTok)")
    print("=" * 60)

    # 1. Download do YouTube
    media = download_youtube_video(url)
    
    # 2. Transcrição com Timestamps
    transcript = transcribe_audio(media["audio_path"])
    
    # 3. Análise de Viralidade com IA
    viral_clips = find_viral_moments(transcript, max_clips=num_clips)
    
    # Subpasta para este vídeo
    video_output_dir = OUTPUT_DIR / media["id"]
    video_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. Geração dos Cortes Verticais
    print(f"\n[4/4] ✂️ Renderizando {len(viral_clips)} cortes verticais (9:16)...")
    summary = []
    
    for idx, clip in enumerate(viral_clips, 1):
        filename = f"corte_{idx:02d}.mp4"
        out_path = video_output_dir / filename
        
        print(f"\n🔹 Processando Corte #{idx} ({clip['start_time']}s até {clip['end_time']}s)")
        print(f"   Hook: \"{clip.get('hook_phrase', 'N/A')}\"")
        print(f"   Título sugerido: {clip.get('suggested_title', '')}")
        print(f"   Hashtags: {' '.join(clip.get('hashtags', []))}")
        
        create_vertical_clip(
            video_path=media["video_path"],
            start_time=clip["start_time"],
            end_time=clip["end_time"],
            output_path=str(out_path)
        )
        
        clip_data = {
            "clip_number": idx,
            "file": filename,
            "path": str(out_path),
            "start_time": clip["start_time"],
            "end_time": clip["end_time"],
            "duration": round(clip["end_time"] - clip["start_time"], 2),
            "suggested_title": clip.get("suggested_title", ""),
            "hook_phrase": clip.get("hook_phrase", ""),
            "reason": clip.get("reason", ""),
            "hashtags": clip.get("hashtags", [])
        }
        summary.append(clip_data)

    # Salva relatório de metadados para postagem
    metadata_file = video_output_dir / "postagens.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"🎉 SUCESSO! Cortes finalizados e salvos em:")
    print(f"📁 {video_output_dir}")
    print(f"📄 Metadados salvos em: {metadata_file}")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automação de cortes virais para TikTok a partir do YouTube")
    parser.add_argument("url", help="URL do vídeo ou live do YouTube")
    parser.add_argument("--clips", "-c", type=int, default=MAX_CLIPS, help=f"Quantidade de clipes (padrão: {MAX_CLIPS})")
    
    args = parser.parse_args()
    process_video(args.url, args.clips)
