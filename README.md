# 🎬 Clip Farm Pro Automático (YouTube ➡️ TikTok / Reels / Shorts)

Automação inteligente e profissional para esteiras de **Clip Farm**. O sistema ingere vídeos e transmissões ao vivo do YouTube, transcreve com timestamps palavra por palavra, analisa a retenção e picos sonoros com IA (Google Gemini), e renderiza vídeos verticais (9:16) com **legendas dinâmicas estilo TikTok/Alex Hormozi**, thumbnails automáticas e relatórios de postagem.

---

## ⚡ Principais Funcionalidades

1. **Transcrição Dinâmica com Faster-Whisper:** Detecção de fala com timestamps precisos no nível de palavra (`word_timestamps`).
2. **Análise de Viralidade e Ganchos (IA Gemini):** Identificação de trechos de até 1 minuto focados nos primeiros 3 segundos de gancho (Hook), clímax e quebra de expectativa.
3. **Detecção de Picos de Volume Sonoro:** Mapeia gargalhadas, gritos e reações exaltadas no áudio para guiar a seleção dos melhores momentos.
4. **Legendas Dinâmicas TikTok / Hormozi (`.ass`):** Legendas estilizadas com alto contraste, caixa alta e borda escura aplicadas diretamente no vídeo via FFmpeg.
5. **Múltiplos Layouts 9:16 (1080x1920):**
   - `blur`: Fundo desfocado dinâmico + vídeo original centralizado nítido.
   - `split`: Tela dividida (perfeito para streamer em cima + jogo/conteúdo embaixo).
6. **Gerador Automático de Capas/Thumbnails:** Extrai o frame de maior impacto para capa do TikTok.
7. **Monitor de Canais (`channel_watcher.py`):** Modo 100% autônomo que monitora canais do YouTube e dispara o corte assim que um vídeo novo é lançado.

---

## 📂 Estrutura do Projeto

```text
clip_farm/
├── config.py                 # Configurações globais
├── downloader.py             # Download via yt-dlp e extração de áudio
├── transcriber.py            # Transcrição com timestamps por palavra
├── audio_analyzer.py         # Detecção de picos de energia e reações sonoras
├── viral_analyzer.py         # IA avaliando ganchos, relevância e hashtags
├── subtitles_generator.py    # Gerador de legendas dinâmicas estilo Hormozi (.ass)
├── video_editor.py           # Renderização vertical 9:16 e extração de thumbnails
├── channel_watcher.py        # Robô monitor de canais para automação contínua
├── main.py                   # Orquestrador da esteira (CLI)
├── requirements.txt          # Dependências
├── .env.example              # Modelo de variáveis de ambiente
└── storage/
    ├── temp/                 # Arquivos temporários de processamento
    └── output/               # Cortes, capas e postagens.json prontos
```

---

## ⚙️ Pré-requisitos

1. **Python 3.10+**
2. **FFmpeg** instalado no sistema e acessível pelo terminal.
3. Chave gratuita da API do Gemini ([Google AI Studio](https://aistudio.google.com/app/apikey)).

---

## 🚀 Como Usar

### 1. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar o `.env`
Copie o `.env.example` para `.env` e coloque sua chave:
```env
GEMINI_API_KEY=sua_chave_aqui
```

### 3. Gerar cortes de um vídeo do YouTube
```bash
python main.py "https://www.youtube.com/watch?v=SEU_VIDEO"
```

**Opções disponíveis no comando:**
- `--clips 5`: Quantidade de cortes a serem gerados.
- `--layout split`: Alterna para layout de tela dividida (streamer + gameplay).
- `--no-subs`: Desativa as legendas automáticas.

### 4. Modo Robô Autônomo (Watcher)
Para deixar o robô monitorando canais e cortando vídeos novos sozinho:
1. Abra `channel_watcher.py` e adicione os links dos canais na lista `canais_para_monitorar`.
2. Execute:
```bash
python channel_watcher.py
```
