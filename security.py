import os
import re
import json
import time
import ipaddress
import threading
from pathlib import Path
from collections import defaultdict, deque
from urllib.parse import urlparse
from cryptography.fernet import Fernet, InvalidToken


# ==============================================================================
# 1. CRIPTOGRAFIA DE DADOS EM REPOUSO (AES-128-CBC + HMAC-SHA256 via Fernet)
# ==============================================================================
def _get_key_path() -> Path:
    """
    Armazena a chave mestra FORA da pasta compartilhada do projeto,
    no perfil local do usuário do Windows (%LOCALAPPDATA%).
    Assim, mesmo que alguém copie a pasta do projeto na rede,
    os arquivos cifrados (.tiktok_session.json) continuam ilegíveis.
    """
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        key_dir = Path(local_app_data) / "ClipFarmStudio"
    else:
        key_dir = Path.home() / ".clip_farm_studio"
    key_dir.mkdir(parents=True, exist_ok=True)
    return key_dir / ".secret.key"


def _get_fernet() -> Fernet:
    key_path = _get_key_path()
    if key_path.exists():
        key = key_path.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass
    return Fernet(key)


def save_encrypted_json(file_path: Path, data: dict) -> None:
    """Salva um dicionário em disco cifrado com Fernet (criptografia autenticada)."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    f = _get_fernet()
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    token = f.encrypt(raw).decode("ascii")
    envelope = {"encrypted": True, "v": 1, "payload": token}
    with open(file_path, "w", encoding="utf-8") as fp:
        json.dump(envelope, fp, indent=2)


def load_encrypted_json(file_path: Path) -> dict:
    """
    Lê um arquivo JSON cifrado. Se encontrar um arquivo antigo em texto puro,
    migra automaticamente para o formato criptografado em disco.
    """
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as fp:
            content = json.load(fp)
    except Exception:
        return {}

    if isinstance(content, dict) and content.get("encrypted") is True and "payload" in content:
        try:
            f = _get_fernet()
            decrypted = f.decrypt(content["payload"].encode("ascii"))
            return json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, Exception):
            # Chave diferente ou arquivo adulterado
            return {}

    # Migração automática de arquivo antigo em texto puro -> criptografado
    if isinstance(content, dict) and content:
        try:
            save_encrypted_json(file_path, content)
        except Exception:
            pass
        return content

    return {}


# ==============================================================================
# 2. PREVENÇÃO DE VAZAMENTO DE DADOS EM LOGS E MENSAGENS DE ERRO (DLP)
# ==============================================================================
_SENSITIVE_PATTERNS = [
    # Chaves Google / Gemini
    (re.compile(r"(AIza[0-9A-Za-z\-_]{20,})"), "[API_KEY_OCULTA]"),
    (re.compile(r"(AQ\.[0-9A-Za-z\-_]{20,})"), "[API_KEY_OCULTA]"),
    # Cookies / Session IDs / Tokens hex longos
    (re.compile(r"(sessionid(?:_ss)?\s*[=:]\s*)[A-Za-z0-9_\-\.]{12,}", re.IGNORECASE), r"\1[SESSAO_OCULTA]"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{12,}", re.IGNORECASE), r"\1[TOKEN_OCULTO]"),
    (re.compile(r"([\"']?(?:password|senha|token|secret|api_key|session_id|access_token)[\"']?\s*[=:]\s*[\"']?)([^\"'\s,}]{4,})", re.IGNORECASE), r"\1[OCULTO]"),
    # E-mails
    (re.compile(r"([a-zA-Z0-9_.+-]{2})[a-zA-Z0-9_.+-]*(@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"), r"\1***\2"),
    # Telefones brasileiros / internacionais
    (re.compile(r"(\+?\d{2}\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4})"), "[TELEFONE_OCULTO]"),
]


def redact_sensitive(text: str) -> str:
    """Remove/mascara credenciais, tokens, e-mails e telefones antes de logar ou exibir."""
    if not text:
        return ""
    result = str(text)
    for pattern, repl in _SENSITIVE_PATTERNS:
        result = pattern.sub(repl, result)
    return result


# ==============================================================================
# 3. VALIDAÇÃO ANTI-PATH TRAVERSAL, ANTI-SSRF E ANTI-ENV INJECTION
# ==============================================================================
_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_\-\.]+$")
_ALLOWED_MEDIA_EXTS = {".mp4", ".jpg", ".jpeg"}
_ALLOWED_YT_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
}
_ALLOWED_PRIVACY = {"SELF_ONLY", "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR"}
_ALLOWED_WHISPER = {"tiny", "base", "small", "medium", "large-v3"}
_ALLOWED_LAYOUTS = {"blur", "split"}


def safe_media_path(base_dir: Path, video_id: str, filename: str) -> Path:
    """
    Impede Path Traversal (../../.env, etc.) validando segmentos, extensão e
    garantindo que o caminho resolvido esteja estritamente dentro de base_dir.
    """
    if not video_id or not filename:
        raise ValueError("Identificador de mídia inválido.")
    if ".." in video_id or ".." in filename or "/" in video_id or "\\" in video_id or "/" in filename or "\\" in filename:
        raise ValueError("Tentativa de acesso fora do diretório permitido bloqueada.")
    if not _SAFE_SEGMENT_RE.match(video_id) or not _SAFE_SEGMENT_RE.match(filename):
        raise ValueError("Caracteres não permitidos no nome do arquivo.")

    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_MEDIA_EXTS:
        raise ValueError("Tipo de arquivo não permitido.")

    base_resolved = base_dir.resolve()
    target = (base_resolved / video_id / filename).resolve()
    if not target.is_relative_to(base_resolved):
        raise ValueError("Acesso bloqueado: caminho fora da pasta de mídia.")
    return target


def validate_youtube_url(url: str) -> str:
    """
    Previne SSRF e Argument Injection no yt-dlp:
    aceita exclusivamente URLs HTTPS válidas de domínios oficiais do YouTube.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL inválida.")
    clean = url.strip()
    if len(clean) > 500 or clean.startswith("-") or any(c in clean for c in ("\n", "\r", "\x00", " ")):
        raise ValueError("Formato de URL não permitido.")

    parsed = urlparse(clean)
    if parsed.scheme not in ("https", "http"):
        raise ValueError("Apenas links HTTP/HTTPS do YouTube são permitidos.")
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_YT_HOSTS:
        raise ValueError("Por segurança, apenas URLs oficiais do YouTube são aceitas.")
    return clean


def sanitize_env_value(value: str) -> str:
    """Previne injeção de variáveis arbitrárias no arquivo .env."""
    if not value:
        return ""
    clean = value.replace("\r", "").replace("\n", "").replace("\x00", "").strip()
    if len(clean) > 512:
        raise ValueError("Valor de configuração excede o tamanho máximo permitido.")
    return clean


def validate_layout(layout: str) -> str:
    return layout if layout in _ALLOWED_LAYOUTS else "blur"


def validate_privacy(privacy: str) -> str:
    return privacy if privacy in _ALLOWED_PRIVACY else "SELF_ONLY"


def validate_whisper_model(model: str) -> str:
    return model if model in _ALLOWED_WHISPER else "base"


# ==============================================================================
# 4. ANTI-INVASÃO DE REDE, ANTI-CSRF E RATE LIMITER POR IP
# ==============================================================================
def is_private_or_local_ip(ip_str: str) -> bool:
    """Permite apenas conexões locais (localhost) ou da rede interna (LAN)."""
    if not ip_str:
        return False
    if ip_str in ("127.0.0.1", "::1", "localhost", "testclient"):
        return True
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
    except ValueError:
        return False


def is_allowed_origin(origin: str, allowed_origins: set) -> bool:
    """Valida cabeçalho Origin/Referer para prevenir ataques CSRF vindos de sites externos."""
    if not origin:
        return True
    parsed = urlparse(origin)
    normalized = f"{parsed.scheme}://{parsed.netloc}".lower()
    if normalized in allowed_origins:
        return True
    # Permite qualquer IP privado na mesma porta caso o IP LAN mude
    host = (parsed.hostname or "").lower()
    return is_private_or_local_ip(host)


class RateLimiter:
    """Limitador de taxa em memória por IP para conter flood, DoS e força bruta."""

    def __init__(self):
        self._lock = threading.Lock()
        self._buckets: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._buckets[key]
            cutoff = now - window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= max_requests:
                return False
            q.append(now)
            return True


# ==============================================================================
# 5. CABEÇALHOS HTTP DE SEGURANÇA (HARDENING)
# ==============================================================================
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
    "X-XSS-Protection": "1; mode=block",
    "Cache-Control": "no-store, max-age=0",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' data:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
}
