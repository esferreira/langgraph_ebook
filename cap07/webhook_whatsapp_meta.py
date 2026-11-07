# Arquivo: webhook_whatsapp_meta.py
# Integração com a WhatsApp Business Cloud API (Meta Oficial)
import os
import httpx
from fastapi import Request, Query, HTTPException

VERIFY_TOKEN_META = os.getenv(
    "META_VERIFY_TOKEN", "meu_token_verificacao"
)
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "EAAG...")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_ID", "102030405060")

# 1. Rota GET exigida pela Meta para validar a propriedade do Webhook
@app.get("/webhook/whatsapp")
async def verificar_webhook_meta(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if (
        hub_mode == "subscribe"
        and hub_verify_token == VERIFY_TOKEN_META
    ):
        # A Meta exige devolver o hub.challenge como inteiro/texto puro
        return int(hub_challenge)
    raise HTTPException(
        status_code=403, detail="Token de verificação inválido"
    )


# 2. Rota POST que recebe o payload aninhado real da Meta Cloud API
@app.post("/webhook/whatsapp")
async def receber_whatsapp_meta(request: Request):
    payload = await request.json()

    try:
        evento = payload["entry"][0]["changes"][0]["value"]
        mensagens = evento.get("messages", [])
        if not mensagens:
            # Eventos de status (entregue/lido) não possuem "messages"
            return {"status": "evento_de_status_ignorado"}

        msg_obj = mensagens[0]
        telefone_cliente = msg_obj["from"]       # Ex: "5511999998888"
        texto_recebido = msg_obj["text"]["body"] # Texto do cliente
    except (KeyError, IndexError):
        return {"status": "formato_nao_suportado"}

    # Padronizamos o thread_id com o prefixo "wa_"
    config_whatsapp = {
        "configurable": {
            "thread_id": f"wa_{telefone_cliente}"
        }
    }

    # Invocação assíncrona (não trava o event loop do FastAPI)
    resultado = await grafo_empresa.ainvoke(
        {"messages": [HumanMessage(content=texto_recebido)]},
        config=config_whatsapp
    )
    resposta_ia = resultado["messages"][-1].content

    # Envio assíncrono da resposta para a Graph API oficial da Meta
    url_meta = (
        f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    )
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    corpo_envio = {
        "messaging_product": "whatsapp",
        "to": telefone_cliente,
        "type": "text",
        "text": {"body": resposta_ia},
    }

    async with httpx.AsyncClient(timeout=10.0) as cliente_http:
        await cliente_http.post(
            url_meta, json=corpo_envio, headers=headers
        )

    return {"status": "processado"}
