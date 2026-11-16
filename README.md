# 🎬 Clip Farm Studio Pro (Desktop + 📱 Mobile + 📲 Auto-Post TikTok com Login)

Automação completa e profissional para esteiras de **Clip Farm**. O sistema ingere vídeos e lives do YouTube, transcreve com Faster-Whisper, detecta os momentos de maior retenção com IA (Google Gemini), renderiza em 9:16 vertical com **legendas dinâmicas estilo TikTok/Alex Hormozi**, thumbnails automáticas e **PUBLICA AUTOMATICAMENTE NO TIKTOK** com sua conta conectada!

---

## 🔑 Como Conectar sua Conta do TikTok

Você pode conectar sua conta de 2 formas simples na aba **"⚙️ Configurações / Login"**:

### Opção 1: Login com Usuário e Senha (Direto)
1. Acesse a aba **Configurações / Login** no site.
2. Digite seu **Usuário** (ex: `@seucanal`) e sua **Senha do TikTok**.
3. Clique em **"🚀 Conectar Conta do TikTok"**.
4. A tela exibirá: `🟢 TikTok Conectado: @seu_usuario`.

### Opção 2: Login com Session ID (Cookie) ou API Oficial
Se preferir não digitar sua senha, você pode colar seu cookie `sessionid` ou seu token da API de Desenvolvedor.

---

## 📱 Como Usar no Celular (Link Gerado pelo Site)

O próprio site gera o link e o QR Code em tempo real:
1. No topo do site, clique em **"📱 Abrir no Celular"**.
2. O site mostrará:
   - O link gerado para seu celular (ex: `http://172.17.174.110:8888`).
   - Botão **"💬 Enviar Link para meu WhatsApp"** (envia o link pronto para o seu WhatsApp para você clicar no smartphone).
   - **QR Code** para apontar a câmera do celular e entrar direto!

---

## 📂 Arquivos do Projeto

```text
clip_farm/
├── INICIAR_CLIP_FARM.bat     # Executável de 1 clique sem terminal preto
├── INICIAR_SILENCIOSO.vbs    # Script VBScript que roda em background
├── tiktok_auth.py            # Autenticação de conta TikTok (SessionID e API)
├── auto_publisher.py         # Módulo de postagem automática no TikTok
├── run_server.py             # Servidor com detecção de IP local
├── server.py                 # Backend FastAPI com Background Tasks e API de Login
├── static/
│   └── index.html            # Dashboard com Login TikTok, Terminal e Player 9:16
├── ffmpeg_helper.py          # Auto-detecção do binário do FFmpeg
├── downloader.py             # Download via yt-dlp e extração de áudio
├── transcriber.py            # Transcrição Faster-Whisper com timestamps
├── audio_analyzer.py         # Detecção de picos de energia sonoros
├── viral_analyzer.py         # IA avaliando retenção, ganchos e hashtags
├── subtitles_generator.py    # Geração de legendas animadas (.ass)
├── video_editor.py           # Renderização vertical 9:16 e thumbnails
├── channel_watcher.py        # Robô autônomo monitor de canais
├── main.py                   # CLI Desktop tradicional
└── requirements.txt          # Dependências Python
```
