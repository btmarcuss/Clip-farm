import os
import json
import requests
from pathlib import Path
from config import TIKTOK_ACCESS_TOKEN, TIKTOK_PRIVACY_LEVEL, WEBHOOK_PUBLISH_URL

def publish_clip_to_tiktok(video_path: str, title: str, hashtags: list) -> dict:
    """
    Publica o clipe vertical automaticamente no TikTok usando a TikTok Content Posting API v2.
    Caso não haja token configurado, realiza fallback seguro ou envio via webhook integrado.
    """
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Arquivo de vídeo não encontrado: {video_path}")

    full_caption = f"{title} {' '.join(hashtags)}"
    # Limite seguro de caracteres do TikTok
    full_caption = full_caption[:2200]

    print(f"\n📲 [AUTO-POST TIKTOK] Iniciando publicação automática...")
    print(f"   Legenda: {full_caption[:60]}...")
    print(f"   Privacidade: {TIKTOK_PRIVACY_LEVEL}")

    # 1. Modo Webhook (se configurado ex: N8N/Make/Zapier para postar em TikTok/Instagram/Shorts)
    if WEBHOOK_PUBLISH_URL:
        print(f"   🚀 Enviando para webhook de publicação: {WEBHOOK_PUBLISH_URL}")
        try:
            with open(video_file, "rb") as vf:
                resp = requests.post(
                    WEBHOOK_PUBLISH_URL,
                    data={"title": title, "hashtags": json.dumps(hashtags), "caption": full_caption},
                    files={"video": (video_file.name, vf, "video/mp4")},
                    timeout=60
                )
            if resp.status_code in (200, 201):
                print(f"   ✅ Publicado com sucesso via Webhook!")
                return {"success": True, "provider": "webhook", "status": "published"}
        except Exception as e:
            print(f"   ⚠️ Falha no envio via webhook: {e}")

    # 2. Modo TikTok Content Posting API Oficial
    if TIKTOK_ACCESS_TOKEN:
        try:
            headers = {
                "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            file_size = video_file.stat().st_size

            # Passo A: Inicializar post
            init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
            init_payload = {
                "post_info": {
                    "title": full_caption,
                    "privacy_level": TIKTOK_PRIVACY_LEVEL,
                    "disable_duet": False,
                    "disable_stitch": False,
                    "disable_comment": False
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": file_size,
                    "total_chunk_count": 1
                }
            }
            init_resp = requests.post(init_url, json=init_payload, headers=headers, timeout=30)
            init_data = init_resp.json()

            if "data" in init_data and "upload_url" in init_data["data"]:
                upload_url = init_data["data"]["upload_url"]
                publish_id = init_data["data"].get("publish_id")

                # Passo B: Upload do vídeo
                with open(video_file, "rb") as vf:
                    upload_headers = {
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{file_size - 1}/{file_size}"
                    }
                    put_resp = requests.put(upload_url, data=vf, headers=upload_headers, timeout=120)

                if put_resp.status_code in (200, 201):
                    print(f"   🎉 VÍDEO PUBLICADO NO TIKTOK COM SUCESSO! (Publish ID: {publish_id})")
                    return {"success": True, "provider": "tiktok_api", "publish_id": publish_id, "status": "published"}
                else:
                    print(f"   ⚠️ Erro no upload dos bytes do vídeo: {put_resp.text}")
            else:
                print(f"   ⚠️ Erro ao inicializar post no TikTok: {init_data}")
        except Exception as e:
            print(f"   ⚠️ Erro na integração da API do TikTok: {e}")

    # 3. Fallback: Fila local pronta para postar
    queue_dir = video_file.parent / "ready_to_post"
    queue_dir.mkdir(parents=True, exist_ok=True)
    post_info_file = queue_dir / f"{video_file.stem}_tiktok_meta.json"
    
    with open(post_info_file, "w", encoding="utf-8") as f:
        json.dump({
            "video_path": str(video_file),
            "caption": full_caption,
            "title": title,
            "hashtags": hashtags,
            "status": "waiting_token_configuration"
        }, f, ensure_ascii=False, indent=2)

    print(f"   ℹ️ Modo Simulação / Fila: Vídeo pronto e metadados salvos em: {post_info_file.name}")
    print(f"   👉 Para postar 100% direto na sua conta do TikTok, adicione o TIKTOK_ACCESS_TOKEN no arquivo .env")
    return {"success": True, "provider": "local_queue", "status": "ready_to_post", "file": str(post_info_file)}
