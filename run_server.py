import socket
import uvicorn
from server import app

def get_local_ip():
    """Descobre o endereço IP da máquina na rede local Wi-Fi."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Não precisa estar acessível, apenas inicializa a rota
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    print("=" * 65)
    print("📱 SERVIDOR MOBILE DO CLIP FARM INICIADO!")
    print("=" * 65)
    print(f"👉 No seu computador:  http://localhost:{port}")
    print(f"👉 NO SEU CELULAR:      http://{local_ip}:{port}")
    print("=" * 65)
    print("💡 Dica no Celular: No Chrome ou Safari, clique em 'Compartilhar' >")
    print("   'Adicionar à Tela de Início' para usar como Aplicativo (PWA)!")
    print("=" * 65)
    
    uvicorn.run(app, host="0.0.0.0", port=port)
