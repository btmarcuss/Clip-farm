# 🎬 Clip Farm Pro (YouTube ➡️ TikTok / Reels / Shorts) + 📱 Mobile PWA

Automação inteligente e profissional para esteiras de **Clip Farm**. O sistema ingere vídeos e transmissões ao vivo do YouTube, transcreve com timestamps palavra por palavra, analisa a retenção e picos sonoros com IA (Google Gemini), e renderiza vídeos verticais (9:16) com **legendas dinâmicas estilo TikTok/Alex Hormozi**, thumbnails automáticas e relatórios de postagem.

**Agora com suporte completo para CELULAR (PWA / Web Mobile)!** Você pode controlar toda a esteira direto do seu smartphone Android ou iPhone.

---

## 📱 Como Usar no Celular (Passo a Passo)

Você não precisa instalar bibliotecas pesadas no seu celular: a máquina/servidor processa tudo com GPU e o seu celular funciona como controle remoto completo e player nativo.

1. **Inicie o servidor mobile no computador:**
   ```bash
   python run_server.py
   ```
   O terminal exibirá um link como:
   ```text
   👉 NO SEU CELULAR: http://192.168.1.X:8000
   ```

2. **Abra o link no navegador do celular (Chrome ou Safari)**
   - Ambos os aparelhos (PC e Celular) devem estar no mesmo Wi-Fi.

3. **Instale como Aplicativo Nativo (PWA)**:
   - **No Android (Chrome):** Toque nos 3 pontinhos e selecione *"Adicionar à tela inicial"*.
   - **No iPhone (Safari):** Toque no botão de compartilhar e selecione *"Adicionar à Tela de Início"*.

4. **Direto do seu Celular**:
   - Cole links de lives ou podcasts do YouTube.
   - Escolha o número de cortes e o layout (Blur ou Split).
   - Acompanhe a barra de progresso em tempo real.
   - Assista aos vídeos verticais 9:16 no player.
   - Copie títulos e hashtags com 1 toque e baixe o vídeo direto para a galeria do celular.

---

## ⚡ Principais Funcionalidades

1. **📱 Interface Mobile-First PWA:** Desenvolvida sob medida para smartphones, fluida e com suporte a atalhos.
2. **🎙️ Transcrição Dinâmica com Faster-Whisper:** Detecção de fala com timestamps precisos no nível de palavra (`word_timestamps`).
3. **🧠 Análise de Viralidade e Ganchos (IA Gemini):** Identificação de trechos de até 1 minuto focados nos primeiros 3 segundos de gancho (Hook), clímax e quebra de expectativa.
4. **🔊 Detecção de Picos de Volume Sonoro:** Mapeia gargalhadas, gritos e reações exaltadas no áudio para guiar a seleção dos melhores momentos.
5. **📝 Legendas Dinâmicas TikTok / Hormozi (`.ass`):** Legendas estilizadas com alto contraste, caixa alta e borda escura aplicadas diretamente no vídeo.
6. **📐 Múltiplos Layouts 9:16 (1080x1920):**
   - `blur`: Fundo desfocado dinâmico + vídeo original centralizado nítido.
   - `split`: Tela dividida (perfeito para streamer em cima + jogo/conteúdo embaixo).
7. **🖼️ Gerador Automático de Capas/Thumbnails:** Extrai o frame de maior impacto para capa do TikTok.
8. **🤖 Monitor de Canais (`channel_watcher.py`):** Modo 100% autônomo que monitora canais do YouTube e dispara o corte assim que um vídeo novo é lançado.

---

## 📂 Estrutura do Projeto

```text
clip_farm/
├── run_server.py             # Inicia o servidor mobile e exibe o IP local
├── server.py                 # API FastAPI (Jobs, WebSockets/Polling e Streaming)
├── static/
│   └── index.html            # Interface Mobile-First PWA (Player 9:16 + Ações)
├── config.py                 # Configurações globais
├── downloader.py             # Download via yt-dlp e extração de áudio
├── transcriber.py            # Transcrição com timestamps por palavra
├── audio_analyzer.py         # Detecção de picos de energia e reações sonoras
├── viral_analyzer.py         # IA avaliando ganchos, relevância e hashtags
├── subtitles_generator.py    # Gerador de legendas dinâmicas estilo Hormozi (.ass)
├── video_editor.py           # Renderização vertical 9:16 e extração de thumbnails
├── channel_watcher.py        # Robô monitor de canais para automação contínua
├── main.py                   # Orquestrador via Linha de Comando (CLI)
├── requirements.txt          # Dependências
└── storage/
    ├── temp/                 # Arquivos temporários de processamento
    └── output/               # Cortes, capas e postagens.json prontos
```

---

## ⚙️ Pré-requisitos e Instalação

```bash
cd clip_farm
pip install -r requirements.txt
copy .env.example .env
```
*(Adicione sua `GEMINI_API_KEY` gratuita gerada no [Google AI Studio](https://aistudio.google.com/app/apikey) no arquivo `.env`)*.
