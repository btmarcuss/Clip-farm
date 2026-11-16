import os
from pathlib import Path
from dotenv import load_dotenv

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent

# Carrega variáveis do .env (se existir)
load_dotenv(BASE_DIR / ".env")

# Configurações de Rede / Servidor
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8888))

# Configurações de IA e Modelos
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Parâmetros de Cortes
MAX_CLIPS = int(os.getenv("MAX_CLIPS", 3))
MIN_CLIP_DURATION = int(os.getenv("MIN_CLIP_DURATION", 30))
MAX_CLIP_DURATION = int(os.getenv("MAX_CLIP_DURATION", 60))

# Layout Padrão: "blur" ou "split"
DEFAULT_LAYOUT = os.getenv("DEFAULT_LAYOUT", "blur")

# Habilitar legendas automáticas animadas (True/False)
ENABLE_SUBTITLES = os.getenv("ENABLE_SUBTITLES", "True").lower() in ("true", "1", "yes")

# Publicação Automática no TikTok
AUTO_POST = os.getenv("AUTO_POST", "False").lower() in ("true", "1", "yes")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_PRIVACY_LEVEL = os.getenv("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY")
WEBHOOK_PUBLISH_URL = os.getenv("WEBHOOK_PUBLISH_URL", "")

# Diretórios de armazenamento
STORAGE_DIR = BASE_DIR / "storage"
TEMP_DIR = STORAGE_DIR / "temp"
OUTPUT_DIR = STORAGE_DIR / "output"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
