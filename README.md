# 🎬 Clip Farm Pro (YouTube ➡️ TikTok / Reels / Shorts) + 📲 Auto-Post TikTok

Automação inteligente e profissional para esteiras de **Clip Farm**. O sistema ingere vídeos e transmissões ao vivo do YouTube, transcreve com timestamps palavra por palavra, analisa a retenção e picos sonoros com IA (Google Gemini), renderiza vídeos verticais (9:16) com **legendas dinâmicas estilo TikTok/Alex Hormozi**, thumbnails automáticas e **PUBLICA AUTOMATICAMENTE NO TIKTOK** com um único comando ou toque no celular!

---

## ⚡ Novidade: Postagem 100% Automática no TikTok

Agora você não precisa baixar nem postar manualmente. Ao acionar o corte, o sistema:
1. Gera os cortes em 9:16 com as legendas animadas.
2. Extrai o título magnético e as 5 hashtags com IA.
3. Faz o upload e publicação imediata na sua conta do TikTok via **TikTok Content Posting API v2** (ou webhook integrado para múltiplas redes como Shorts e Reels).

### Como Usar o Auto-Post:

#### Pelo Celular (Interface Mobile PWA):
1. Acesse o app no celular (`http://IP-DO-PC:8000`).
2. Mantenha o toggle **"📲 Postar no TikTok Direto"** ativado.
3. Cole o link e clique em **"🚀 Cortar e Publicar Automático"**.

#### Pelo Terminal / Linha de Comando:
Basta adicionar a flag `--autopost`:
```bash
python main.py "https://www.youtube.com/watch?v=SEU_VIDEO" --autopost
```

---

## 🔑 Configuração das Credenciais no `.env`

No seu arquivo `.env`:
```env
# Chave da IA Gemini
GEMINI_API_KEY=sua_chave_aqui

# Ativar Auto-Post por padrão
AUTO_POST=True

# Token de acesso do TikTok (obtido no portal de desenvolvedores do TikTok)
TIKTOK_ACCESS_TOKEN=seu_token_aqui

# Privacidade inicial: "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS" ou "SELF_ONLY" (rascunho privado para aprovação)
TIKTOK_PRIVACY_LEVEL=SELF_ONLY

# (Opcional) Webhook para disparar automações no Make / Zapier / N8N
WEBHOOK_PUBLISH_URL=
```

*(Se você ainda não tiver o `TIKTOK_ACCESS_TOKEN` configurado, o sistema salva o pacote pronto na pasta `storage/output/.../ready_to_post/` sem dar erro).*

---

## 📂 Estrutura do Projeto

```text
clip_farm/
├── auto_publisher.py         # Módulo de postagem automática no TikTok / Webhooks
├── run_server.py             # Servidor Mobile PWA
├── server.py                 # Backend FastAPI com Background Tasks e Auto-Post
├── static/
│   └── index.html            # Interface Mobile com botão de Auto-Post
├── config.py                 # Configurações globais
├── downloader.py             # Download via yt-dlp e extração de áudio
├── transcriber.py            # Transcrição com timestamps por palavra
├── audio_analyzer.py         # Detecção de picos de energia e reações sonoras
├── viral_analyzer.py         # IA avaliando ganchos, relevância e hashtags
├── subtitles_generator.py    # Gerador de legendas dinâmicas estilo Hormozi (.ass)
├── video_editor.py           # Renderização vertical 9:16 e extração de thumbnails
├── channel_watcher.py        # Robô monitor de canais para automação contínua
├── main.py                   # Orquestrador via CLI com flag --autopost
├── requirements.txt          # Dependências
└── storage/
    ├── temp/                 # Arquivos temporários de processamento
    └── output/               # Cortes, capas, postagens.json e logs de publicação
```

---

## 🚀 Instalação e Execução

```bash
pip install -r requirements.txt
python run_server.py
```
Acesse no celular pelo endereço exibido no terminal e desfrute da esteira 100% automatizada!
