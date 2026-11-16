import time
import json
from pathlib import Path
import yt_dlp
from config import BASE_DIR
from main import process_video

HISTORY_FILE = BASE_DIR / "storage" / "processed_history.json"

def load_history() -> set:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_history(processed_ids: set):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed_ids), f, indent=2)

def check_channel_for_new_videos(channel_url: str, max_check: int = 3) -> list:
    """Verifica os vídeos mais recentes de um canal sem baixá-los."""
    ydl_opts = {
        'extract_flat': True,
        'playlistend': max_check,
        'quiet': True,
        'no_warnings': True
    }
    
    new_videos = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        if 'entries' in info:
            for entry in info['entries']:
                if entry and 'id' in entry:
                    new_videos.append({
                        "id": entry['id'],
                        "url": f"https://www.youtube.com/watch?v={entry['id']}",
                        "title": entry.get('title', 'Sem título')
                    })
    return new_videos

def watch_channels(channels: list, interval_minutes: int = 30):
    """
    Monitor contínuo (Modo Robô 100% Autônomo):
    Fica observando os canais cadastrados. Assim que sai vídeo novo,
    corta automaticamente e salva na pasta de saída.
    """
    print(f"🤖 [ROBÔ CLIP FARM ATIVADO]")
    print(f"Observando {len(channels)} canais a cada {interval_minutes} minutos...\n")

    history = load_history()

    while True:
        for ch in channels:
            print(f"🔍 Checando canal: {ch}")
            try:
                recent_videos = check_channel_for_new_videos(ch)
                for vid in recent_videos:
                    if vid["id"] not in history:
                        print(f"\n🚨 NOVO VÍDEO DETECTADO: {vid['title']}")
                        print(f"Iniciando esteira automática de cortes...")
                        
                        process_video(vid["url"])
                        
                        history.add(vid["id"])
                        save_history(history)
            except Exception as e:
                print(f"⚠️ Erro ao checar canal {ch}: {e}")

        print(f"\n⏳ Aguardando próximo ciclo de monitoramento ({interval_minutes} min)...")
        time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    # Exemplo: adicione as URLs dos canais que deseja monitorar
    canais_para_monitorar = [
        # "https://www.youtube.com/@NomeDoCanal/videos",
    ]
    if not canais_para_monitorar:
        print("💡 Adicione URLs de canais na lista 'canais_para_monitorar' em channel_watcher.py")
    else:
        watch_channels(canais_para_monitorar, interval_minutes=20)
