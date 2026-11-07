# arquivo: notificadores_reais.py
import html
import os
import smtplib
from email.message import EmailMessage
import requests


# 1. TELEGRAM (Oficial e gratuito via @BotFather)
# Usamos parse_mode="HTML" para que sublinhados em `pedido_482`
# nunca quebrem a formatação da mensagem (erro 400 do Markdown).
def enviar_alerta_telegram(
    mensagem: str, thread_id: str, token_aprovacao: str
) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    tid_seguro = html.escape(thread_id)
    msg_segura = html.escape(mensagem)
    tok_seguro = html.escape(token_aprovacao)

    texto_html = (
        f"🚨 <b>APROVAÇÃO HUMANA NECESSÁRIA</b>\n"
        f"📂 <b>Protocolo:</b> <code>{tid_seguro}</code>\n\n"
        f"{msg_segura}\n\n"
        f"👉 <i>Responda:</i>\n"
        f"<code>SIM {tid_seguro} {tok_seguro}</code> ou "
        f"<code>NAO {tid_seguro} {tok_seguro}</code>"
    )

    if not bot_token or not chat_id:
        print("\n" + "=" * 64)
        print("📱 [SIMULAÇÃO TELEGRAM - parse_mode=HTML]")
        print(texto_html)
        print("=" * 64)
        return True

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto_html,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=10)
    return resp.status_code == 200


# 2. WHATSAPP (Em produção comercial, use a WhatsApp Cloud API da Meta
# ou provedores oficiais como Twilio/Zenvia).
def enviar_alerta_whatsapp(
    numero_destino: str,
    mensagem: str,
    thread_id: str,
    token_aprovacao: str,
) -> bool:
    cloud_api_url = os.getenv("WHATSAPP_CLOUD_API_URL", "")
    bearer_token = os.getenv("WHATSAPP_BEARER_TOKEN", "")

    texto_zap = (
        f"🚨 *APROVAÇÃO PENDENTE - {thread_id}*\n\n"
        f"{mensagem}\n\n"
        f"Para aprovar, responda:\n"
        f"SIM {thread_id} {token_aprovacao}\n"
        f"Para recusar, responda:\n"
        f"NAO {thread_id} {token_aprovacao}"
    )

    if not cloud_api_url or not bearer_token:
        print("\n" + "=" * 64)
        print(f"🟢 [WHATSAPP OFICIAL -> {numero_destino}]")
        print(texto_zap)
        print("=" * 64)
        return True

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto_zap},
    }
    resp = requests.post(
        cloud_api_url, json=payload, headers=headers, timeout=10
    )
    return resp.status_code in (200, 201)


# 3. E-MAIL COM LINK PARA PÁGINA DE CONFIRMAÇÃO (GET -> POST)
def enviar_alerta_email(
    email_gerente: str,
    mensagem: str,
    thread_id: str,
    token_aprovacao: str,
    url_servidor: str = "http://localhost:8000",
) -> bool:
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    # O link no e-mail apenas abre a página de confirmação (GET).
    # A aprovação exige clicar no botão que envia POST com o token!
    link_painel = (
        f"{url_servidor}/confirmar-reembolso"
        f"?thread_id={thread_id}&token={token_aprovacao}"
    )

    corpo_email = (
        f"Olá, Gerente Financeiro.\n\n"
        f"O processo '{thread_id}' aguarda sua autorização:\n\n"
        f"{mensagem}\n\n"
        f"Acesse a página segura abaixo para confirmar ou recusar:\n"
        f"🔒 {link_painel}\n"
    )

    if not smtp_user or not smtp_pass:
        print("\n" + "=" * 64)
        print(f"📧 [SIMULAÇÃO E-MAIL -> {email_gerente}]")
        print(corpo_email.strip())
        print("=" * 64)
        return True

    msg = EmailMessage()
    msg["Subject"] = f"[Aprovação Necessária] Pedido #{thread_id}"
    msg["From"] = smtp_user
    msg["To"] = email_gerente
    msg.set_content(corpo_email)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)
    return True
