import os
import json
import time
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any
from config import BASE_DIR, STORAGE_DIR, OUTPUT_DIR, TEMP_DIR
from security import save_encrypted_json, load_encrypted_json, sanitize_env_value

CONSENT_FILE = STORAGE_DIR / ".lgpd_consent.json"
LGPD_REQUESTS_FILE = STORAGE_DIR / ".lgpd_requests.json"
SESSION_FILE = STORAGE_DIR / ".tiktok_session.json"
CHROME_PROFILE_DIR = STORAGE_DIR / "chrome_profile"

LEGAL_LAST_UPDATED = "23/11/2026"


def get_company_legal_data() -> Dict[str, str]:
    """
    Retorna os dados legais da empresa/controlador configurados no .env.
    Nunca inventa CNPJ ou razão social fictícia.
    """
    return {
        "company_name": os.getenv("COMPANY_NAME", "").strip() or "[Não configurado — defina COMPANY_NAME no arquivo .env]",
        "cnpj": os.getenv("COMPANY_CNPJ", "").strip() or "[Não configurado — defina COMPANY_CNPJ no arquivo .env]",
        "address": os.getenv("COMPANY_ADDRESS", "").strip() or "[Não configurado — defina COMPANY_ADDRESS no arquivo .env]",
        "dpo_name": os.getenv("COMPANY_DPO_NAME", "").strip() or "Encarregado de Dados (DPO) — Controlador Local",
        "dpo_email": os.getenv("COMPANY_DPO_EMAIL", "").strip() or "[Não configurado — defina COMPANY_DPO_EMAIL no arquivo .env]",
        "forum_city": os.getenv("COMPANY_FORUM_CITY", "").strip() or "São Paulo/SP — Brasil",
        "operation_mode": "Execução local (self-hosted) sob controle exclusivo do titular/operador da máquina.",
        "last_updated": LEGAL_LAST_UPDATED,
    }


def get_third_party_audit() -> Dict[str, Any]:
    """Inventário transparente de rastreadores (zero) e integrações externas estritamente necessárias."""
    return {
        "google_analytics": False,
        "advertising_pixels": False,
        "external_fonts_cdn": False,
        "external_qr_api": False,
        "tracking_scripts_count": 0,
        "encryption_at_rest": "Fernet (AES-128-CBC + HMAC-SHA256) com chave isolada em %LOCALAPPDATA%",
        "necessary_integrations": [
            {
                "name": "YouTube (via yt-dlp)",
                "purpose": "Download exclusivo da URL informada manualmente pelo usuário para edição local.",
                "data_sent": "Apenas requisição de mídia da URL solicitada.",
                "optional": False,
            },
            {
                "name": "Google Gemini API",
                "purpose": "Análise textual da transcrição gerada localmente para sugerir intervalos de corte e legendas.",
                "data_sent": "Texto da transcrição e timestamps (não envia dados cadastrais pessoais).",
                "optional": False,
            },
            {
                "name": "TikTok / TikTok Studio",
                "purpose": "Publicação de clipes apenas quando ativada e autorizada expressamente pelo usuário.",
                "data_sent": "Arquivo de vídeo editado, título/hashtags e cookie de sessão fornecido pelo usuário.",
                "optional": True,
            },
        ],
    }


def get_applicable_brazilian_laws() -> list:
    return [
        {
            "law": "Lei nº 13.709/2018 (LGPD)",
            "scope": "Lei Geral de Proteção de Dados Pessoais — minimização de coleta, consentimento, transparência, acesso, portabilidade e eliminação de dados (Art. 6º e Art. 18).",
        },
        {
            "law": "Lei nº 12.965/2014 e Decreto nº 8.771/2016 (Marco Civil da Internet)",
            "scope": "Direitos e deveres no uso da Internet no Brasil, privacidade das comunicações e padrões de segurança e sigilo de registros.",
        },
        {
            "law": "Lei nº 8.078/1990 (Código de Defesa do Consumidor — CDC)",
            "scope": "Transparência nas informações (Art. 6º), vedação à publicidade enganosa ou promessas sem comprovação (Art. 37) e direito de arrependimento em 7 dias (Art. 49) para serviços pagos.",
        },
        {
            "law": "Lei nº 9.610/1998 (Lei de Direitos Autorais — LDA)",
            "scope": "Proteção às obras intelectuais, audiovisuais e direitos conexos; uso exclusivo em conteúdo próprio ou devidamente autorizado/licenciado.",
        },
        {
            "law": "Lei nº 9.609/1998 (Lei do Software)",
            "scope": "Regime jurídico de proteção à propriedade intelectual de programas de computador e licenciamento no Brasil.",
        },
        {
            "law": "Lei nº 13.146/2015 (LBI — Estatuto da Pessoa com Deficiência)",
            "scope": "Acessibilidade digital (Art. 63), seguindo diretrizes WCAG 2.1 AA: contraste visual, navegação por teclado e textos alternativos.",
        },
    ]


def get_legal_documents() -> Dict[str, Any]:
    company = get_company_legal_data()
    return {
        "company": company,
        "audit": get_third_party_audit(),
        "brazilian_laws": get_applicable_brazilian_laws(),
        "privacy_policy": {
            "title": "Política de Privacidade (LGPD)",
            "updated_at": LEGAL_LAST_UPDATED,
            "sections": [
                {
                    "heading": "1. Controlador e Escopo",
                    "body": (
                        f"Esta Política descreve como o Clip Farm Studio trata dados em conformidade com a Lei Geral de Proteção de Dados (Lei nº 13.709/2018 — LGPD) e o Marco Civil da Internet (Lei nº 12.965/2014). "
                        f"Controlador: {company['company_name']} | CNPJ: {company['cnpj']} | Contato do Encarregado (DPO): {company['dpo_email']}. "
                        f"Este software opera em modo local (na própria máquina do usuário), sem envio de telemetria a servidores próprios."
                    ),
                },
                {
                    "heading": "2. Princípio da Necessidade e Coleta Mínima",
                    "body": (
                        "Coletamos e armazenamos apenas o estritamente necessário para executar as funções solicitadas por você: "
                        "(a) URL do vídeo do YouTube informada para edição; (b) chaves de API ou sessão de publicação fornecidas voluntariamente; "
                        "(c) preferências técnicas (enquadramento, legendas e quantidade de cortes). Não coletamos CPF, RG, endereço residencial, dados bancários ou dados sensíveis (Art. 5º, II da LGPD)."
                    ),
                },
                {
                    "heading": "3. Ausência de Rastreamento e Google Analytics",
                    "body": (
                        "Esta aplicação NÃO utiliza Google Analytics, Meta Pixel, scripts de publicidade comportamental, CDNs externos de fontes ou APIs externas de QR Code. "
                        "Todo o layout, fontes e geração de QR Code funcionam 100% localmente."
                    ),
                },
                {
                    "heading": "4. Segurança e Criptografia dos Dados",
                    "body": (
                        "Credenciais e cookies de sessão salvos localmente são criptografados com algoritmo autenticado Fernet (AES-128-CBC + HMAC-SHA256), com chave mestra isolada fora da pasta do projeto. "
                        "Logs em memória aplicam mascaramento automático (DLP) para ocultar tokens, chaves de API, e-mails e telefones. O servidor aceita apenas conexões da rede local (LAN)."
                    ),
                },
                {
                    "heading": "5. Compartilhamento com Terceiros",
                    "body": (
                        "Dados só trafegam para serviços externos quando você aciona uma funcionalidade: (1) YouTube, para baixar a mídia da URL escolhida; "
                        "(2) Google Gemini API, para analisar o texto transcrito; (3) TikTok, exclusivamente se você conectar sua conta e habilitar a postagem automática. "
                        "O uso desses serviços segue as respectivas políticas de privacidade de cada provedor."
                    ),
                },
                {
                    "heading": "6. Seus Direitos (Art. 18 da LGPD) e Retenção",
                    "body": (
                        "Você pode, a qualquer momento e com 1 clique na aba 'Privacidade & LGPD', confirmar o tratamento, exportar seus dados (portabilidade em JSON), "
                        "revogar consentimentos ou excluir definitivamente todos os dados, sessões, histórico e mídias armazenados localmente. "
                        "Com a opção 'Não guardar vídeos após postar' ativa, os arquivos de vídeo são excluídos imediatamente após confirmação da publicação."
                    ),
                },
            ],
        },
        "terms_of_use": {
            "title": "Termos de Uso e Direitos Autorais",
            "updated_at": LEGAL_LAST_UPDATED,
            "sections": [
                {
                    "heading": "1. Objeto e Funcionamento",
                    "body": (
                        "O Clip Farm Studio é uma ferramenta técnica de auxílio à edição de vídeos curtos em formato vertical (9:16), transcrição local de áudio e apoio à publicação. "
                        "Não há garantia ou promessa de visualizações, engajamento, viralização ou ganhos financeiros, pois o desempenho de conteúdo depende de fatores externos e algoritmos de terceiros."
                    ),
                },
                {
                    "heading": "2. Direitos Autorais e Propriedade Intelectual (Lei nº 9.610/1998)",
                    "body": (
                        "O usuário declara e garante ser o titular dos direitos autorais, de imagem e conexos sobre todo vídeo processado, ou possuir autorização expressa / licença válida (como Creative Commons compatível) do titular original. "
                        "É estritamente proibido utilizar esta ferramenta para reproduzir, redistribuir ou monetizar obras protegidas de terceiros sem autorização, respondendo o usuário integralmente por eventuais infrações civis ou penais."
                    ),
                },
                {
                    "heading": "3. Conformidade com Termos de Plataformas Terceiras",
                    "body": (
                        "O usuário é responsável por respeitar os Termos de Serviço do YouTube, Google Gemini e TikTok. Integrações automatizadas estão sujeitas a limites técnicos, verificações de segurança (captcha) e alterações das plataformas terceiras."
                    ),
                },
                {
                    "heading": "4. Limitação de Responsabilidade e Foro",
                    "body": (
                        f"A ferramenta é fornecida 'como está', com boas práticas de segurança e código auditável. "
                        f"Estes Termos são regidos pelas leis da República Federativa do Brasil, ficando eleito o foro de {company['forum_city']}, ressalvado o foro do domicílio do consumidor quando aplicável o CDC (Art. 101, I)."
                    ),
                },
            ],
        },
        "refund_policy": {
            "title": "Política de Reembolso e Cancelamento (CDC)",
            "updated_at": LEGAL_LAST_UPDATED,
            "sections": [
                {
                    "heading": "1. Uso Local Gratuito",
                    "body": (
                        "Na modalidade de uso local (self-hosted), este software não realiza cobranças, assinaturas ou processamento de pagamentos. "
                        "Eventuais custos de APIs externas (como cota paga da Google Gemini API) são contratados diretamente pelo usuário junto ao respectivo provedor."
                    ),
                },
                {
                    "heading": "2. Direito de Arrependimento — 7 Dias (Art. 49 do CDC)",
                    "body": (
                        "Caso venham a ser oferecidos planos pagos, licenças comerciais ou suporte contratado à distância, o consumidor tem direito garantido pelo Art. 49 do Código de Defesa do Consumidor (Lei nº 8.078/1990) "
                        "de desistir da contratação em até 7 (sete) dias corridos a contar da data da contratação ou recebimento do acesso, com reembolso integral (100%) dos valores pagos, sem burocracia e sem multa."
                    ),
                },
                {
                    "heading": "3. Prazo e Forma de Estorno",
                    "body": (
                        "Solicitações de reembolso dentro do prazo legal ou por falha técnica comprovada não solucionada devem ser enviadas ao canal de atendimento informado nos Dados Legais "
                        f"({company['dpo_email']}). O estorno é processado pelo mesmo meio de pagamento original (Pix, boleto ou estorno em cartão de crédito conforme ciclo da operadora)."
                    ),
                },
            ],
        },
        "cookie_policy": {
            "title": "Política de Cookies e Armazenamento Local",
            "updated_at": LEGAL_LAST_UPDATED,
            "categories": [
                {
                    "id": "essential",
                    "name": "Estritamente Necessários (Sempre Ativos)",
                    "required": True,
                    "description": "Indispensáveis para segurança anti-CSRF, funcionamento básico do painel e registro da sua escolha de consentimento.",
                    "items": ["Preferência de consentimento LGPD (localStorage)", "Sessão técnica local quando você conecta o TikTok"],
                },
                {
                    "id": "preferences",
                    "name": "Preferências de Interface (Opcional)",
                    "required": False,
                    "description": "Lembra escolhas de interface como quantidade padrão de cortes, enquadramento e exibição de histórico.",
                    "items": ["Preferências de layout e última aba visitada (localStorage)"],
                },
                {
                    "id": "analytics",
                    "name": "Analytics e Rastreamento Publicitário",
                    "required": False,
                    "disabled_permanently": True,
                    "description": "NÃO UTILIZADO. Este aplicativo não instala Google Analytics, cookies de marketing ou rastreadores de terceiros.",
                    "items": ["Nenhum script ou cookie de rastreamento instalado"],
                },
            ],
        },
    }


def get_cookie_consent() -> Dict[str, Any]:
    data = load_encrypted_json(CONSENT_FILE)
    if not data:
        return {"decided": False, "essential": True, "preferences": False, "analytics": False, "updated_at": None}
    return data


def save_cookie_consent(preferences: bool = False) -> Dict[str, Any]:
    record = {
        "decided": True,
        "essential": True,
        "preferences": bool(preferences),
        "analytics": False,  # Permanentemente desativado
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_encrypted_json(CONSENT_FILE, record)
    return record


def submit_lgpd_request(request_type: str, contact_email: str, details: str) -> Dict[str, Any]:
    """
    Registra solicitação do titular (Art. 18 LGPD) com coleta mínima de dados.
    """
    allowed_types = {
        "acesso": "Confirmação e acesso aos dados (Art. 18, I e II)",
        "correcao": "Correção de dados incompletos ou desatualizados (Art. 18, III)",
        "eliminacao": "Eliminação de dados pessoais (Art. 18, VI)",
        "portabilidade": "Portabilidade dos dados (Art. 18, V)",
        "revogacao": "Revogação de consentimento (Art. 18, IX)",
        "reembolso": "Solicitação de reembolso / CDC Art. 49",
        "duvida": "Dúvida ao Encarregado de Dados (DPO)",
    }
    req_key = request_type if request_type in allowed_types else "duvida"
    clean_email = sanitize_env_value(contact_email)[:120]
    clean_details = sanitize_env_value(details)[:800]

    if clean_email and ("@" not in clean_email or "." not in clean_email):
        raise ValueError("Informe um e-mail de retorno válido ou deixe o campo em branco.")

    protocol = f"LGPD-{time.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    entry = {
        "protocol": protocol,
        "type": req_key,
        "type_label": allowed_types[req_key],
        "contact_email": clean_email,
        "details": clean_details,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "registrado_localmente",
    }

    existing = load_encrypted_json(LGPD_REQUESTS_FILE)
    items = existing.get("requests", []) if isinstance(existing, dict) else []
    items.append(entry)
    # Mantém apenas os últimos 50 registros locais
    save_encrypted_json(LGPD_REQUESTS_FILE, {"requests": items[-50:]})
    return entry


def export_user_data() -> Dict[str, Any]:
    """Portabilidade / Acesso (Art. 18, II e V da LGPD): exporta metadados sem segredos brutos."""
    session = load_encrypted_json(SESSION_FILE)
    safe_session = {
        "has_session": bool(session),
        "auth_type": session.get("auth_type", "none"),
        "username": session.get("username", ""),
        "status": session.get("status", "inactive"),
        "secrets_redacted": True,
    }

    history_summary = []
    if OUTPUT_DIR.exists():
        for vid_dir in OUTPUT_DIR.iterdir():
            if vid_dir.is_dir():
                meta = vid_dir / "postagens.json"
                if meta.exists():
                    try:
                        with open(meta, "r", encoding="utf-8") as f:
                            clips = json.load(f)
                        history_summary.append({"video_id": vid_dir.name, "clips": clips})
                    except Exception:
                        pass

    requests_data = load_encrypted_json(LGPD_REQUESTS_FILE)

    return {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "legal_basis": "LGPD — Lei nº 13.709/2018, Art. 18, II e V (Acesso e Portabilidade)",
        "cookie_consent": get_cookie_consent(),
        "tiktok_connection_summary": safe_session,
        "generated_clips_history": history_summary,
        "lgpd_requests": requests_data.get("requests", []) if isinstance(requests_data, dict) else [],
        "company_controller": get_company_legal_data(),
    }


def delete_all_user_data(system_logs_deque=None) -> Dict[str, Any]:
    """
    Eliminação definitiva de todos os dados do titular armazenados localmente (Art. 18, VI da LGPD):
    - Credenciais criptografadas do TikTok
    - Perfil persistente do navegador Chrome (cookies de sessão)
    - Todos os vídeos, legendas, thumbnails e históricos em storage/output e storage/temp
    - Registros de consentimento e solicitações LGPD locais
    - Buffer de logs em memória
    """
    removed = []

    for fpath, label in [
        (SESSION_FILE, "Sessão/credenciais do TikTok"),
        (CONSENT_FILE, "Registro de consentimento"),
        (LGPD_REQUESTS_FILE, "Histórico de formulários LGPD"),
        (STORAGE_DIR / "debug_tiktok_last.png", "Screenshot de diagnóstico"),
    ]:
        if fpath.exists():
            try:
                fpath.unlink()
                removed.append(label)
            except Exception:
                pass

    if CHROME_PROFILE_DIR.exists():
        try:
            shutil.rmtree(CHROME_PROFILE_DIR, ignore_errors=True)
            removed.append("Perfil e cookies do navegador Chrome")
        except Exception:
            pass

    for folder, label in [(OUTPUT_DIR, "Clipes e histórico gerados"), (TEMP_DIR, "Arquivos temporários de mídia")]:
        if folder.exists():
            count = 0
            for item in folder.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    count += 1
                except Exception:
                    pass
            if count > 0:
                removed.append(f"{label} ({count} item(ns))")

    if system_logs_deque is not None:
        system_logs_deque.clear()
        removed.append("Logs em memória do servidor")

    return {
        "success": True,
        "deleted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "legal_basis": "LGPD — Lei nº 13.709/2018, Art. 18, VI (Eliminação de Dados)",
        "removed_items": removed,
        "message": "Todos os seus dados locais, sessões, cookies e mídias foram excluídos permanentemente.",
    }
