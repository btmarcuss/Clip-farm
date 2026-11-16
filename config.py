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

# Layout Padrão: "blur" (vídeo central + fundo borrado) ou "split" (tela dividida streamer + jogo/conteúdo)
DEFAULT_LAYOUT = os.getenv("DEFAULT_LAYOUT", "blur")

# Habilitar legendas automáticas animadas por padrão (True/False)
ENABLE_SUBTITLES = os.getenv("ENABLE_SUBTITLES", "True").lower() in ("true", "1", "yes")

# Diretórios de armazenamento
STORAGE_DIR = BASE_DIR / "storage"
TEMP_DIR = STORAGE_DIR / "temp"
OUTPUT_DIR = STORAGE_DIR / "output"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
