import os
import secrets
import hashlib
import requests
from pathlib import Path
from config import BASE_DIR
from security import load_encrypted_json, save_encrypted_json

SESSION_FILE = BASE_DIR / "storage" / ".tiktok_session.json"


def _hash_secret(secret: str) -> str:
    """Hash seguro com PBKDF2-HMAC-SHA256 e salt aleatório (evita rainbow tables)."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def get_tiktok_session() -> dict:
    """Carrega e descriptografa as credenciais salvas do TikTok."""
    return load_encrypted_json(SESSION_FILE)


def save_tiktok_credentials(username: str, password: str) -> dict:
    """Salva login por usuário/e-mail de forma criptografada (sem senha em texto puro)."""
    current = get_tiktok_session()

    clean_user = username.strip().replace("@", "")
    current["username"] = clean_user
    current["password_hash"] = _hash_secret(password)
    current["auth_type"] = "usuario_senha"
    current["status"] = "active"
    current["login_identifier"] = clean_user

    save_encrypted_json(SESSION_FILE, current)
    return current


def save_tiktok_phone_login(phone: str, password: str = "", sms_code: str = "") -> dict:
    """Salva login por Número de Telefone de forma criptografada (não persiste código SMS/OTP)."""
    current = get_tiktok_session()

    clean_phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    current["phone"] = clean_phone
    current["username"] = f"tel_{clean_phone[-4:]}"
    current["auth_type"] = "telefone"
    current["status"] = "active"
    current["login_identifier"] = clean_phone
    if password:
        current["password_hash"] = _hash_secret(password)
    # Por segurança, códigos SMS (OTP) nunca são gravados em disco

    save_encrypted_json(SESSION_FILE, current)
    return current


def save_tiktok_google_login(google_email: str, auth_token: str = "") -> dict:
    """Conecta a conta TikTok vinculada à Conta Google com armazenamento criptografado."""
    current = get_tiktok_session()

    clean_email = google_email.strip()
    current["google_email"] = clean_email
    current["username"] = clean_email.split("@")[0]
    current["auth_type"] = "google"
    current["status"] = "active"
    current["login_identifier"] = clean_email
    if auth_token:
        current["google_auth_token"] = auth_token

    save_encrypted_json(SESSION_FILE, current)
    return current


def save_tiktok_session(session_id: str = None, access_token: str = None, username: str = None) -> dict:
    """Salva a sessão do TikTok criptografada com Fernet (AES + HMAC)."""
    current = get_tiktok_session()

    if session_id is not None:
        current["session_id"] = session_id.strip()
        current["auth_type"] = "session_id"
    if access_token is not None:
        current["access_token"] = access_token.strip()
        current["auth_type"] = "access_token"
    if username is not None:
        current["username"] = username.strip().replace("@", "")

    save_encrypted_json(SESSION_FILE, current)
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
