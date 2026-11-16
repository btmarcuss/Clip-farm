import os
from pathlib import Path
from dotenv import load_dotenv

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent

# Carrega variáveis do .env (se existir)
load_dotenv(BASE_DIR / ".env")

# Configurações de API e Modelos
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Parâmetros de Cortes
MAX_CLIPS = int(os.getenv("MAX_CLIPS", 3))
MIN_CLIP_DURATION = int(os.getenv("MIN_CLIP_DURATION", 30))
MAX_CLIP_DURATION = int(os.getenv("MAX_CLIP_DURATION", 60))

# Diretórios de armazenamento
STORAGE_DIR = BASE_DIR / "storage"
TEMP_DIR = STORAGE_DIR / "temp"
OUTPUT_DIR = STORAGE_DIR / "output"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
