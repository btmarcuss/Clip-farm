# 🎬 Clip Farm Studio Pro (Desktop + 📱 Mobile PWA + 📲 Auto-Post TikTok)

Automação completa e profissional para esteiras de **Clip Farm**. O sistema ingere vídeos e lives do YouTube, transcreve com Faster-Whisper, detecta os momentos de maior retenção com IA (Google Gemini), renderiza em 9:16 vertical com **legendas dinâmicas estilo TikTok/Alex Hormozi**, thumbnails automáticas e **PUBLICA AUTOMATICAMENTE NO TIKTOK** com 1 clique!

---

## 💻 Versão Desktop & 📱 Versão Mobile (Tudo em Um)

O projeto foi desenhado de forma adaptativa e intuitiva:
- **No Desktop:** Painel Widescreen completo em 2 colunas com controle total, abas de configuração visual das chaves de API, monitor de progresso e visualizador de vídeos lado a lado.
- **No Celular:** Interface touch fluida estilo TikTok PWA instalável na tela inicial.
- **No Terminal (CLI):** Comando tradicional via linha de comando para automações em scripts ou cronjobs.

---

## ⚡ Como Iniciar no Computador (100% Silencioso)

Neste computador, **todas as dependências já estão instaladas e configuradas**!

Basta dar **duplo clique no arquivo**:
```text
INICIAR_CLIP_FARM.bat  (ou INICIAR_SILENCIOSO.vbs)
```
- O servidor sobe em segundo plano **sem abrir nenhuma janela preta de terminal**.
- O navegador abrirá automaticamente em `http://localhost:8888`.
- Todos os logs, status de download, Whisper e FFmpeg aparecem na aba **"💻 Terminal Logs"** dentro do próprio site!
- Para encerrar o servidor, basta clicar no botão vermelho **"🛑 Desligar Servidor"** no topo da página.

---

## ⚙️ Configuração Visual Direto na Tela

Você não precisa abrir arquivos no bloco de notas para configurar:
1. Abra a aplicação e clique na aba **"⚙️ Configurações"**.
2. Cole sua chave gratuita do **Google Gemini API** (gerada no [Google AI Studio](https://aistudio.google.com/app/apikey)).
3. Cole o token do TikTok (se desejar a publicação 100% automática).
4. Clique em **"💾 Salvar Configurações"**.

---

## 📱 Como Usar no Celular

Ao rodar o `INICIAR_CLIP_FARM.bat`, o terminal exibirá:
```text
👉 NO SEU CELULAR: http://192.168.X.X:8888
```
Basta digitar esse endereço no navegador do celular (Chrome ou Safari) conectado no mesmo Wi-Fi e adicionar à tela inicial.

---

## 🖥️ Uso via Linha de Comando (CLI Desktop)

Se preferir utilizar via terminal:
```bash
# Corte básico
python main.py "https://www.youtube.com/watch?v=SEU_VIDEO"

# Corte com publicação automática direta no TikTok
python main.py "https://www.youtube.com/watch?v=SEU_VIDEO" --autopost

# Tela dividida (streamer + gameplay)
python main.py "https://www.youtube.com/watch?v=SEU_VIDEO" --layout split --clips 5
```

---

## 📂 Arquivos do Projeto

```text
clip_farm/
├── INICIAR_CLIP_FARM.bat     # Executável de 1 clique no Windows
├── INSTALAR_ATUALIZAR.bat    # Instalador automático de dependências
├── run_server.py             # Inicializador do servidor com detecção de IP
├── server.py                 # Backend FastAPI com Background Tasks e API de Config
├── static/
│   └── index.html            # Dashboard Responsivo (Desktop Widescreen + Mobile PWA)
├── ffmpeg_helper.py          # Auto-detecção do binário do FFmpeg
├── downloader.py             # Download via yt-dlp e extração de áudio
├── transcriber.py            # Transcrição Faster-Whisper com timestamps
├── audio_analyzer.py         # Detecção de picos de energia sonoros
├── viral_analyzer.py         # IA avaliando retenção, ganchos e hashtags
├── subtitles_generator.py    # Geração de legendas animadas (.ass)
├── video_editor.py           # Renderização vertical 9:16 e thumbnails
├── auto_publisher.py         # Publicação direta na TikTok API e Webhooks
├── channel_watcher.py        # Robô autônomo monitor de canais
├── main.py                   # CLI Desktop tradicional
└── requirements.txt          # Dependências Python
```
