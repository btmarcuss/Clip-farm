# 🎬 Clip Farm Studio Pro (Desktop + 📱 Mobile + 📲 Auto-Post TikTok com Login)

Automação completa e profissional para esteiras de **Clip Farm**. O sistema ingere vídeos e lives do YouTube, transcreve com Faster-Whisper, detecta os momentos de maior retenção com IA (Google Gemini), renderiza em 9:16 vertical com **legendas dinâmicas estilo TikTok/Alex Hormozi**, thumbnails automáticas e **PUBLICA AUTOMATICAMENTE NO TIKTOK** com sua conta conectada!

---

## 🔑 Como Conectar sua Conta do TikTok (Sem Burocracia)

Você pode conectar sua conta de 2 formas simples na aba **"⚙️ Configurações / Login"**:

### Opção 1: Login com Session ID (Recomendado & Direto em 15 segundos)
Não precisa de conta de desenvolvedor verificada nem burocracia de aprovação:
1. Abra o **[tiktok.com](https://www.tiktok.com)** no seu navegador e faça login na sua conta normalmente.
2. Pressione **F12** no teclado (Ferramentas de Desenvolvedor).
3. Vá na aba **Aplicativo** (ou *Armazenamento*) > **Cookies** > `https://www.tiktok.com`.
4. Procure o cookie chamado **`sessionid`**, copie o valor dele.
5. Cole no campo correspondente no Clip Farm e clique em **"Conectar"**!
6. A tela exibirá: `🟢 TikTok Conectado: @seu_usuario`.

### Opção 2: Token de Desenvolvedor da API Oficial
Para quem possui cadastro como desenvolvedor na TikTok for Developers, basta colar o `access_token` no campo da API Oficial.

---

## ⚡ Como Iniciar no Computador (Modo 100% Silencioso)

Neste computador, **todas as dependências já estão instaladas e configuradas**!

Basta dar **duplo clique no arquivo**:
```text
INICIAR_CLIP_FARM.bat
```
- O servidor sobe em segundo plano **sem abrir nenhuma janela preta de terminal**.
- O navegador abre automaticamente em `http://localhost:8888`.
- Todos os logs, status de download, Whisper e FFmpeg aparecem na aba **"💻 Terminal Logs"** dentro do próprio site!
- Para encerrar o servidor, basta clicar no botão vermelho **"🛑 Desligar Servidor"** no topo da página.

---

## 📱 Como Usar no Celular

Ao iniciar no computador, acesse no celular (conectado no mesmo Wi-Fi):
```text
👉 NO SEU CELULAR: http://192.168.X.X:8888
```
Você pode acionar os cortes, acompanhar os logs e postar no TikTok direto do smartphone!

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
