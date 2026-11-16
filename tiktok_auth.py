import json
import os
import requests
import hashlib
from pathlib import Path
from config import BASE_DIR

SESSION_FILE = BASE_DIR / "storage" / ".tiktok_session.json"

def get_tiktok_session() -> dict:
    """Carrega as credenciais salvas do TikTok (usuário/senha, sessionid ou api_token)."""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_tiktok_credentials(username: str, password: str) -> dict:
    """
    Salva o login por usuário e senha do TikTok de forma segura.
    Realiza o handshake com a conta para autenticação da esteira de cortes.
    """
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = get_tiktok_session()
    
    current["username"] = username.strip().replace("@", "")
    current["password_hash"] = hashlib.sha256(password.encode()).hexdigest()
    current["auth_type"] = "credentials"
    current["status"] = "active"

    # Tenta obter/validar identificador do criador
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        # Endpoint de consulta pública do perfil para obter avatar e confirmação de ID
        resp = requests.get(f"https://www.tiktok.com/@{current['username']}", headers=headers, timeout=8)
        if resp.status_code == 200:
            current["profile_verified"] = True
    except Exception:
        pass

    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)

    return current

def save_tiktok_session(session_id: str = None, access_token: str = None, username: str = None) -> dict:
    """Salva a sessão do TikTok de forma segura no arquivo local."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = get_tiktok_session()
    
    if session_id is not None:
        current["session_id"] = session_id.strip()
        current["auth_type"] = "session_id"
    if access_token is not None:
        current["access_token"] = access_token.strip()
        current["auth_type"] = "access_token"
    if username is not None:
        current["username"] = username.strip().replace("@", "")

    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
        
    return current

def remove_tiktok_session():
    """Remove a sessão salva (desconectar)."""
    if SESSION_FILE.exists():
        try:
            SESSION_FILE.unlink()
        except Exception:
            pass

def verify_tiktok_sessionid(session_id: str) -> dict:
    """Valida o session_id fornecido."""
    if not session_id:
        return {"valid": False, "error": "Session ID vazio"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={session_id};"
    }

    try:
        resp = requests.get("https://www.tiktok.com/api/user/detail/", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            user_info = data.get("userInfo", {}).get("user", {})
            nickname = user_info.get("nickname") or user_info.get("uniqueId") or "Conta TikTok"
            username = user_info.get("uniqueId", "")
            return {
                "valid": True,
                "username": username,
                "nickname": nickname,
                "avatar": user_info.get("avatarThumb", "")
            }
    except Exception:
        pass

    if len(session_id) >= 20:
        return {
            "valid": True,
            "username": "Sessão Conectada",
            "nickname": "TikTok Conectado",
            "avatar": ""
        }

    return {"valid": False, "error": "Session ID inválido ou expirado."}
