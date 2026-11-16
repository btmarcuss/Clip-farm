# 🎬 Clip Farm Automático (YouTube ➡️ TikTok)

Automação inteligente que baixa vídeos e transmissões ao vivo do YouTube, transcreve com Whisper, detecta os momentos com maior potencial viral usando IA (Google Gemini) e gera clipes prontos no formato vertical 9:16 (1080x1920) com duração de até 1 minuto.

---

## 📂 Estrutura de Arquivos

```text
clip_farm/
├── config.py             # Configurações gerais e caminhos
├── downloader.py         # Download e extração de áudio via yt-dlp e ffmpeg
├── transcriber.py        # Transcrição com timestamps via Faster-Whisper
├── viral_analyzer.py     # Detecção de ganchos (hooks) e viralidade com Gemini
├── video_editor.py       # Renderização vertical 9:16 com background blur
├── main.py               # Script principal (CLI)
├── requirements.txt      # Dependências Python
├── .env.example          # Exemplo de variáveis de ambiente
└── storage/
    ├── temp/             # Vídeos baixados do YouTube
    └── output/           # Cortes gerados e relatórios prontos para postar
```

---

## ⚙️ Pré-requisitos

1. **Python 3.10+** instalado.
2. **FFmpeg** instalado e adicionado ao `PATH` do sistema Windows:
   - Para verificar, abra o terminal e digite: `ffmpeg -version`
3. Chave gratuita da API do Google Gemini:
   - Gere em: [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## 🚀 Como Instalar e Rodar

### 1. Criar e ativar o ambiente virtual (Recomendado)
No terminal, dentro da pasta `clip_farm`:
```bash
python -m venv venv
.\venv\Scripts\activate
```

### 2. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar a chave de API
Copie o arquivo `.env.example` para `.env` e insira sua chave:
```bash
copy .env.example .env
```
Abra o `.env` e adicione sua chave:
```env
GEMINI_API_KEY=sua_chave_aqui
```

### 4. Executar a Automação
Basta passar a URL de qualquer vídeo ou gravação de live do YouTube:

```bash
python main.py "https://www.youtube.com/watch?v=SEU_VIDEO_AQUI"
```

Se desejar gerar uma quantidade específica de cortes (ex: 5 cortes):
```bash
python main.py "https://www.youtube.com/watch?v=SEU_VIDEO_AQUI" --clips 5
```

---

## 📦 O Que é Gerado na Saída

Na pasta `storage/output/<ID_DO_VIDEO>/` você encontrará:
- `corte_01.mp4`: Vídeo vertical em 1080x1920 pronto para o TikTok.
- `corte_02.mp4`: Segundo clipe com gancho forte.
- `postagens.json`: Arquivo com os títulos magnéticos sugeridos, frases de abertura (hooks) e hashtags recomendadas para copiar e colar no TikTok.
