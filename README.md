# Clip Farm Studio — Editor Automatizado de Cortes Verticais (9:16)

Ferramenta de execução local (*self-hosted*) para edição automatizada de vídeos curtos verticais (9:16). O sistema baixa o vídeo da URL informada pelo usuário, realiza transcrição local com Faster-Whisper, sugere trechos usando a Google Gemini API, renderiza cortes com legendas sincronizadas e oferece opção de publicação no TikTok (sujeita às políticas e verificações da plataforma).

> **Aviso de Direitos Autorais (Lei nº 9.610/1998):** Utilize esta ferramenta exclusivamente com vídeos de sua autoria ou sobre os quais você possua autorização expressa ou licença compatível. Não há promessa ou garantia de visualizações, alcance ou monetização.

---

## Segurança, Privacidade e Conformidade Legal (Brasil)

- **LGPD (Lei nº 13.709/2018):** Coleta mínima de dados, consentimento granular de cookies/preferências, portabilidade (exportação em JSON) e exclusão definitiva de todos os dados e arquivos locais em 1 clique na aba **Privacidade & LGPD**.
- **Sem Rastreamento:** Zero Google Analytics, zero pixels publicitários, zero CDNs de fontes externas e geração de QR Code 100% local (`/api/qr`).
- **Criptografia e Hardening:** Credenciais criptografadas em repouso com Fernet (AES-128-CBC + HMAC-SHA256) e chave isolada em `%LOCALAPPDATA%`; mascaramento automático de dados sensíveis nos logs (DLP); bloqueio de Path Traversal, SSRF, CSRF, XSS, IPs externos e Rate Limiting.
- **Acessibilidade (WCAG 2.1 AA / LBI — Lei nº 13.146/2015):** Navegação por teclado (`Tab`, `Escape`, *skip link* e foco visível), contraste visual reforçado, textos alternativos, rótulos vinculados (`label`/`aria-*`) e zoom liberado.
- **Leis Brasileiras Aplicáveis:** LGPD (Lei nº 13.709/2018), Marco Civil da Internet (Lei nº 12.965/2014), CDC (Lei nº 8.078/1990 — incluindo Art. 49 de reembolso em 7 dias para serviços pagos), Direitos Autorais (Lei nº 9.610/1998), Lei do Software (Lei nº 9.609/1998) e LBI (Lei nº 13.146/2015).

---

## Dados Legais da Empresa / Controlador

Antes de qualquer uso comercial, preencha seus dados reais no arquivo `.env` (consulte `.env.example`):

```ini
COMPANY_NAME=Sua Razão Social
COMPANY_CNPJ=00.000.000/0001-00
COMPANY_ADDRESS=Seu endereço comercial
COMPANY_DPO_NAME=Nome do Encarregado (DPO)
COMPANY_DPO_EMAIL=privacidade@seudominio.com.br
COMPANY_FORUM_CITY=Sua Cidade/UF - Brasil
```

---

## Como Iniciar

1. Copie `.env.example` para `.env` e configure sua `GEMINI_API_KEY`.
2. Execute `INICIAR_CLIP_FARM.bat` (ou `python run_server.py`).
3. Acesse `http://localhost:8888` no computador ou escaneie o QR Code local pelo celular na mesma rede Wi-Fi.
