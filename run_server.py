import os
import sys
import socket
import uvicorn

# Força codificação universal UTF-8 no Windows
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from server import app
from config import SERVER_HOST, SERVER_PORT

def get_local_ip():
    """Descobre o endereço IP da máquina na rede local Wi-Fi."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 65)
    print("📱 SERVIDOR CLIP FARM STUDIO INICIADO COM SUCESSO!")
    print("=" * 65)
    print(f"👉 NO SEU COMPUTADOR: http://localhost:{SERVER_PORT}")
    print(f"👉 NO SEU CELULAR:     http://{local_ip}:{SERVER_PORT}")
    print("=" * 65)
    print("💡 Dica no Celular: No Chrome ou Safari, clique em 'Compartilhar' >")
    print("   'Adicionar à Tela de Início' para usar como Aplicativo (PWA)!")
    print("=" * 65)
    
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        workers=1,
        timeout_keep_alive=300,   # mantém conexões vivas por 5 min
        timeout_graceful_shutdown=30,
        loop="asyncio",
    )
