import os
import sys
import json
import time
import threading
import requests
from pathlib import Path
from typing import Callable, List, Dict, Any, Optional
from config import BASE_DIR, TIKTOK_ACCESS_TOKEN, TIKTOK_PRIVACY_LEVEL, WEBHOOK_PUBLISH_URL
from tiktok_auth import get_tiktok_session

CHROME_PROFILE_DIR = BASE_DIR / "storage" / "chrome_profile"
DEBUG_SCREENSHOT_PATH = BASE_DIR / "storage" / "debug_tiktok_last.png"

# Lock global: o Chrome não permite abrir o mesmo user_data_dir em duas threads simultâneas
_PLAYWRIGHT_LOCK = threading.Lock()


def open_tiktok_login_window() -> dict:
    """Abre o Chrome nativo para o usuário efetuar login no TikTok e salvar a sessão localmente."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "error": "Playwright não está instalado."}

    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print("🌐 Abrindo janela do Google Chrome para login no TikTok...")

    with _PLAYWRIGHT_LOCK:
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(CHROME_PROFILE_DIR),
                    channel="chrome",
                    headless=False,
                    viewport={"width": 1280, "height": 800},
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )
                page = context.new_page()
                page.goto("https://www.tiktok.com/login", timeout=60000)

                start_time = time.time()
                logged_in = False
                while time.time() - start_time < 300:
                    time.sleep(2)
                    try:
                        current_url = page.url.lower()
                        if "/login" not in current_url and "tiktok.com" in current_url:
                            logged_in = True
                            print("🎉 Login no TikTok detectado com sucesso!")
                            time.sleep(2)
                            break
                    except Exception:
                        break

                context.close()
                return {"success": True, "logged_in": logged_in}
        except Exception as e:
            print(f"⚠️ Erro ao abrir navegador de login: {e}")
            return {"success": False, "error": str(e)}


def is_tiktok_browser_logged_in() -> bool:
    """Verifica se há cookies de sessão do TikTok gravados no perfil do Chrome ou Session ID configurado."""
    session_data = get_tiktok_session()
    if session_data.get("session_id"):
        return True
    if not CHROME_PROFILE_DIR.exists():
        return False
    with _PLAYWRIGHT_LOCK:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(CHROME_PROFILE_DIR),
                    channel="chrome",
                    headless=True,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
                )
                cookies = context.cookies("https://www.tiktok.com")
                context.close()
                session_cookies = [c for c in cookies if c.get("name") in ("sessionid", "sessionid_ss", "sid_tt")]
                return len(session_cookies) > 0
        except Exception:
            return False


def _dismiss_modals(page):
    """Fecha rapidamente pop-ups ou modais do TikTok Studio (ex.: 'Ativar verificações automáticas de conteúdo?')."""
    modal_selectors = [
        '.TUXModal-overlay button:has-text("Cancelar")',
        '.TUXModal-overlay button:has-text("Cancel")',
        '.TUXModal-overlay button:has-text("Agora não")',
        '.TUXModal-overlay button:has-text("Not now")',
        '.TUXModal-overlay button:has-text("Entendi")',
        '.TUXModal-overlay button:has-text("Got it")',
        '.TUXModal-overlay button:has-text("Fechar")',
        '.TUXModal-overlay button:has-text("OK")',
        '[data-floating-ui-portal] button:has-text("Cancelar")',
        '[data-floating-ui-portal] button:has-text("Cancel")',
        '[data-floating-ui-portal] button:has-text("Agora não")',
        '[data-floating-ui-portal] button:has-text("Not now")',
        'button:has-text("Entendi")',
        'button:has-text("Got it")',
        '[aria-label="Close"]',
    ]
    for selector in modal_selectors:
        try:
            btn = page.locator(selector).first
            if btn.count() > 0 and btn.is_visible():
                print(f"   🧹 Fechando modal do TikTok Studio ({selector})...")
                btn.click(timeout=1500)
                time.sleep(0.35)
        except Exception:
            pass
    try:
        if page.locator(".TUXModal-overlay").count() > 0:
            page.keyboard.press("Escape")
            time.sleep(0.25)
    except Exception:
        pass


def _confirm_publish_modals(page):
    """Confirma modais extras pós-clique em Publicar (ex.: 'Publicar agora' / 'Continuar')."""
    for selector in [
        'button:has-text("Publicar agora")',
        'button:has-text("Post now")',
        'button:has-text("Publicar mesmo assim")',
        'button:has-text("Post anyway")',
        'button:has-text("Continuar")',
        'button:has-text("Continue")',
    ]:
        try:
            btn = page.locator(selector).first
            if btn.count() > 0 and btn.is_visible():
                print(f"   ✅ Confirmando modal do TikTok: {selector}")
                btn.click(timeout=2000)
                time.sleep(0.5)
        except Exception:
            pass


def _is_publish_confirmed(page) -> bool:
    """Verifica na URL e no texto da página se o TikTok realmente confirmou a publicação."""
    try:
        url_low = page.url.lower()
        if "/content" in url_low or "/manage" in url_low:
            return True
        body_text = page.locator("body").inner_text().lower()
        success_markers = [
            "seu vídeo foi publicado",
            "vídeo publicado",
            "publicação enviada",
            "gerenciar suas publicações",
            "carregar outro vídeo",
            "your video has been uploaded",
            "your video is being uploaded",
            "manage your posts",
            "upload another video",
            "view profile",
            "ver perfil",
        ]
        return any(m in body_text for m in success_markers)
    except Exception:
        return False


def _delete_local_clip_files(video_file: Path) -> bool:
    try:
        video_file.unlink(missing_ok=True)
        video_file.with_suffix(".ass").unlink(missing_ok=True)
        video_file.with_name(f"{video_file.stem}_thumb.jpg").unlink(missing_ok=True)
        print(f"   🗑️ Arquivo local excluído após confirmação de postagem: {video_file.name}")
        return True
    except Exception as e_del:
        print(f"   ⚠️ Aviso ao excluir arquivo local: {e_del}")
        return False


def _upload_single_on_context(context, video_path: str, caption: str, delete_after: bool = True) -> dict:
    """
    Executa o upload de 1 clipe reutilizando um BrowserContext já aberto (sem reiniciar o Chrome!).
    Usa esperas reativas (polling 1s) para máxima velocidade.
    """
    video_file = Path(video_path)
    if not video_file.exists():
        return {"success": False, "status": "failed", "error": f"Arquivo não encontrado: {video_path}"}

    page = context.new_page()
    try:
        t0 = time.monotonic()
        page.goto("https://www.tiktok.com/tiktokstudio/upload", timeout=60000, wait_until="domcontentloaded")

        # Espera reativa: ou redireciona para /login ou o input[type="file"] aparece
        file_input = None
        for _ in range(25):
            if "login" in page.url.lower():
                return {
                    "success": False,
                    "status": "need_login",
                    "error": "Sessão do TikTok expirou. Conecte sua conta novamente na aba Configurações."
                }
            loc = page.locator('input[type="file"]').first
            if loc.count() > 0:
                file_input = loc
                break
            for frame in page.frames:
                try:
                    if frame.locator('input[type="file"]').count() > 0:
                        file_input = frame.locator('input[type="file"]').first
                        break
                except Exception:
                    pass
            if file_input:
                break
            time.sleep(1.0)

        if not file_input or file_input.count() == 0:
            try:
                page.screenshot(path=str(DEBUG_SCREENSHOT_PATH))
            except Exception:
                pass
            return {
                "success": False,
                "status": "failed",
                "error": "Campo de upload do TikTok Studio não encontrado. O vídeo foi mantido para download."
            }

        print(f"   📤 Anexando {video_file.name} ({video_file.stat().st_size / (1024*1024):.1f} MB)...")
        file_input.set_input_files(str(video_file.resolve()))

        # Polling reativo a cada 1.2s aguardando upload finalizar + botão Publicar habilitado (até 90s)
        upload_ready = False
        publish_btn = None
        up_start = time.monotonic()
        while time.monotonic() - up_start < 90:
            time.sleep(1.2)
            _dismiss_modals(page)
            btn = page.locator('button[data-e2e="post_video_button"], button:has-text("Publicar"), button:has-text("Post")').first
            if btn.count() > 0:
                try:
                    is_dis = btn.is_disabled()
                    aria_dis = btn.get_attribute("aria-disabled")
                    body_low = page.locator("body").inner_text().lower()
                    has_uploaded = any(k in body_low for k in ("enviado", "uploaded", "substituir", "replace"))
                    if has_uploaded and not is_dis and aria_dis != "true":
                        upload_ready = True
                        publish_btn = btn
                        print(f"   ✅ Vídeo carregado no TikTok Studio em {time.monotonic() - up_start:.1f}s!")
                        break
                except Exception:
                    pass

        if not upload_ready or publish_btn is None:
            try:
                page.screenshot(path=str(DEBUG_SCREENSHOT_PATH))
            except Exception:
                pass
            return {
                "success": False,
                "status": "failed",
                "error": "Tempo esgotado aguardando o TikTok processar o vídeo. O corte foi mantido para download."
            }

        # Preenche a legenda instantaneamente via insert_text (suporta emojis e acentos sem delay)
        caption_editor = page.locator('div[contenteditable="true"], div.public-DraftEditor-content, textarea').first
        if caption_editor.count() > 0:
            try:
                caption_editor.scroll_into_view_if_needed(timeout=2000)
                caption_editor.click(force=True, timeout=3000)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                time.sleep(0.2)
                page.keyboard.insert_text(caption)
                print("   📝 Legenda e hashtags preenchidas.")
                time.sleep(0.8)
            except Exception as e_cap:
                print(f"   ⚠️ Aviso ao preencher legenda: {e_cap}")

        # Garante zero modais na frente antes de clicar em Publicar
        _dismiss_modals(page)
        print("   🚀 Clicando no botão Publicar...")
        publish_btn.scroll_into_view_if_needed(timeout=3000)
        publish_btn.click(timeout=10000)

        # Polling reativo a cada 1.2s aguardando confirmação real (até 25s)
        published_ok = False
        pub_start = time.monotonic()
        while time.monotonic() - pub_start < 25:
            time.sleep(1.2)
            _confirm_publish_modals(page)
            if _is_publish_confirmed(page):
                published_ok = True
                break

        if not published_ok:
            try:
                page.screenshot(path=str(DEBUG_SCREENSHOT_PATH))
            except Exception:
                pass
            print("   ⚠️ O TikTok não exibiu confirmação de publicação. Mantendo arquivo para download.")
            return {
                "success": False,
                "status": "failed",
                "error": "TikTok não confirmou a publicação (possível captcha ou revisão). Vídeo mantido para download."
            }

        print(f"   🎉 Publicação CONFIRMADA em {time.monotonic() - t0:.1f}s!")
        deleted = _delete_local_clip_files(video_file) if delete_after else False

        return {
            "success": True,
            "provider": "tiktok_browser_automation",
            "status": "published",
            "caption": caption,
            "local_file_deleted": deleted
        }
    except Exception as e:
        print(f"   ⚠️ Falha no upload Playwright: {e}")
        return {
            "success": False,
            "status": "failed",
            "error": f"Erro no envio automático: {str(e)}. Vídeo mantido para download."
        }
    finally:
        try:
            page.close()
        except Exception:
            pass


def _launch_tiktok_context(p):
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(CHROME_PROFILE_DIR),
        channel="chrome",
        headless=True,
        viewport={"width": 1280, "height": 900},
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu",
        ]
    )
    sid = get_tiktok_session().get("session_id")
    if sid:
        context.add_cookies([
            {"name": "sessionid", "value": sid, "domain": ".tiktok.com", "path": "/", "httpOnly": True, "secure": True},
            {"name": "sessionid_ss", "value": sid, "domain": ".tiktok.com", "path": "/", "httpOnly": True, "secure": True},
            {"name": "sid_tt", "value": sid, "domain": ".tiktok.com", "path": "/", "httpOnly": True, "secure": True},
        ])
    return context


def upload_clip_via_playwright(video_path: str, caption: str, delete_after: bool = True) -> dict:
    """Publica um único clipe via Playwright com lock global."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "status": "failed", "error": "Playwright não disponível"}

    with _PLAYWRIGHT_LOCK:
        try:
            with sync_playwright() as p:
                context = _launch_tiktok_context(p)
                try:
                    return _upload_single_on_context(context, video_path, caption, delete_after=delete_after)
                finally:
                    context.close()
        except Exception as e:
            return {"success": False, "status": "failed", "error": str(e)}


def publish_clips_batch(
    clips_specs: List[Dict[str, Any]],
    delete_after_post: bool = True,
    on_progress: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    on_start: Optional[Callable[[int, int], None]] = None
) -> List[Dict[str, Any]]:
    """
    OTIMIZAÇÃO DE LOTE: Abre o Google Chrome UMA ÚNICA VEZ para publicar todos os cortes do job
    em sequência na mesma sessão, economizando ~8-12s de inicialização por corte!
    """
    if not clips_specs:
        return []

    if not is_tiktok_browser_logged_in():
        results = []
        for idx, spec in enumerate(clips_specs, 1):
            if on_start:
                on_start(idx, len(clips_specs))
            res = publish_clip_to_tiktok(
                video_path=spec["video_path"],
                title=spec["title"],
                hashtags=spec["hashtags"],
                delete_after_post=delete_after_post,
            )
            results.append(res)
            if on_progress:
                on_progress(idx, len(clips_specs), res)
        return results

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [
            {"success": False, "status": "failed", "error": "Playwright não disponível", "local_file_deleted": False}
            for _ in clips_specs
        ]

    results = []
    with _PLAYWRIGHT_LOCK:
        try:
            with sync_playwright() as p:
                print(f"\n⚡ [BATCH TIKTOK] Abrindo Chrome 1 única vez para publicar {len(clips_specs)} corte(s)...")
                context = _launch_tiktok_context(p)
                try:
                    for idx, spec in enumerate(clips_specs, 1):
                        if on_start:
                            on_start(idx, len(clips_specs))
                        caption = f"{spec['title']} {' '.join(spec.get('hashtags', []))}"[:2200]
                        print(f"📲 [Batch {idx}/{len(clips_specs)}] Publicando: {Path(spec['video_path']).name}")
                        try:
                            res = _upload_single_on_context(
                                context,
                                video_path=spec["video_path"],
                                caption=caption,
                                delete_after=delete_after_post,
                            )
                        except Exception as e_item:
                            res = {
                                "success": False,
                                "status": "failed",
                                "error": f"Erro inesperado ao publicar: {e_item}. Vídeo mantido para download.",
                                "local_file_deleted": False,
                            }
                        results.append(res)
                        if on_progress:
                            on_progress(idx, len(clips_specs), res)
                        if res.get("status") == "need_login":
                            for _ in clips_specs[idx:]:
                                results.append(res)
                            break
                        # Pequena pausa entre postagens em lote para evitar rate-limit/captcha do TikTok
                        if idx < len(clips_specs):
                            time.sleep(2.0)
                finally:
                    try:
                        context.close()
                    except Exception:
                        pass
        except Exception as e_launch:
            err_res = {
                "success": False,
                "status": "failed",
                "error": f"Erro ao abrir o Chrome para envio em lote: {e_launch}. Vídeos mantidos para download.",
                "local_file_deleted": False,
            }
            while len(results) < len(clips_specs):
                results.append(err_res)
                if on_progress:
                    on_progress(len(results), len(clips_specs), err_res)
    return results


def publish_clip_to_tiktok(video_path: str, title: str, hashtags: list, delete_after_post: bool = True) -> dict:
    """Publica um único clipe (Chrome/Playwright -> API oficial -> Webhook -> Mantido p/ download)."""
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Arquivo de vídeo não encontrado: {video_path}")

    full_caption = f"{title} {' '.join(hashtags)}"[:2200]
    session_data = get_tiktok_session()
    api_token = session_data.get("access_token") or TIKTOK_ACCESS_TOKEN

    last_error = None
    if is_tiktok_browser_logged_in():
        pw_result = upload_clip_via_playwright(video_path, full_caption, delete_after=delete_after_post)
        if pw_result.get("success"):
            return pw_result
        last_error = pw_result.get("error")

    if api_token:
        try:
            headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
            file_size = video_file.stat().st_size
            init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
            init_payload = {
                "post_info": {
                    "title": full_caption,
                    "privacy_level": TIKTOK_PRIVACY_LEVEL,
                    "disable_duet": False,
                    "disable_stitch": False,
                    "disable_comment": False,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": file_size,
                    "total_chunk_count": 1,
                },
            }
            init_resp = requests.post(init_url, json=init_payload, headers=headers, timeout=30)
            init_data = init_resp.json()
            if "data" in init_data and "upload_url" in init_data["data"]:
                upload_url = init_data["data"]["upload_url"]
                publish_id = init_data["data"].get("publish_id")
                with open(video_file, "rb") as vf:
                    put_resp = requests.put(
                        upload_url,
                        data=vf,
                        headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{file_size - 1}/{file_size}"},
                        timeout=120,
                    )
                if put_resp.status_code in (200, 201):
                    deleted = _delete_local_clip_files(video_file) if delete_after_post else False
                    return {"success": True, "provider": "tiktok_api", "publish_id": publish_id, "status": "published", "local_file_deleted": deleted}
        except Exception as e:
            last_error = str(e)

    if WEBHOOK_PUBLISH_URL:
        try:
            with open(video_file, "rb") as vf:
                resp = requests.post(
                    WEBHOOK_PUBLISH_URL,
                    data={"title": title, "hashtags": json.dumps(hashtags), "caption": full_caption},
                    files={"video": (video_file.name, vf, "video/mp4")},
                    timeout=60,
                )
            if resp.status_code in (200, 201):
                deleted = _delete_local_clip_files(video_file) if delete_after_post else False
                return {"success": True, "provider": "webhook", "status": "published", "local_file_deleted": deleted}
        except Exception as e:
            last_error = str(e)

    return {
        "success": False,
        "provider": "local_saved",
        "status": "failed" if last_error else "need_login",
        "error": last_error or "Conecte sua conta do TikTok na aba Configurações para postagem automática.",
        "local_file_deleted": False,
    }
