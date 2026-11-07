# Arquivo: webhook_whatsapp_producao.py
import hashlib
import hmac
from fastapi import BackgroundTasks, Header, HTTPException, Request
import httpx

# Em produção com múltiplos workers/containers, substitua este set em
# memória por uma chave no Redis (ex: redis.set(msg_id, "1", nx=True,
# ex=3600)) e exija APP_SECRET_META via os.environ["APP_SECRET_META"].
MENSAGENS_JA_PROCESSADAS: set[str] = set()
APP_SECRET_META = os.getenv("APP_SECRET_META", "")

async def processar_no_langgraph_e_responder(
    telefone: str, texto: str
):
    """
    Corrotina executada em segundo plano após o webhook liberar 200 OK.
    Usa await .ainvoke() e httpx.AsyncClient sem bloquear o event loop.
    """
    config = {"configurable": {"thread_id": f"wa_{telefone}"}}
    resultado = await grafo_empresa.ainvoke(
        {"messages": [HumanMessage(content=texto)]},
        config=config
    )
    resposta_ia = resultado["messages"][-1].content

    url_meta = (
        f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    )
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    payload_envio = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {"body": resposta_ia},
    }
    async with httpx.AsyncClient(timeout=10.0) as cliente:
        await cliente.post(
            url_meta, json=payload_envio, headers=headers
        )


@app.post("/webhook/whatsapp-producao")
async def webhook_whatsapp_idempotente(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=""),
):
    # 0. Validação HMAC-SHA256 da Meta (mesmo padrão visto no Cap. 5)
    corpo_bruto = await request.body()
    if APP_SECRET_META:
        assinatura_calc = "sha256=" + hmac.new(
            APP_SECRET_META.encode(), corpo_bruto, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(
            x_hub_signature_256, assinatura_calc
        ):
            raise HTTPException(
                status_code=401, detail="X-Hub-Signature-256 inválida"
            )

    payload = await request.json()

    try:
        evento = payload["entry"][0]["changes"][0]["value"]
        mensagens = evento.get("messages", [])
        if not mensagens:
            return {"status": "ignorado"}

        msg_obj = mensagens[0]
        msg_id = msg_obj["id"]            # ID da mensagem (wamid)
        telefone = msg_obj["from"]        # Número do cliente
        texto = msg_obj["text"]["body"]   # Conteúdo de texto
    except (KeyError, IndexError):
        return {"status": "payload_nao_suportado"}

    # 1. Trava de Idempotência: se reenviar o mesmo msg_id, ignoramos
    if msg_id in MENSAGENS_JA_PROCESSADAS:
        return {"status": "duplicata_ignorada", "msg_id": msg_id}

    MENSAGENS_JA_PROCESSADAS.add(msg_id)

    # 2. Agenda a execução do LangGraph em segundo plano
    background_tasks.add_task(
        processar_no_langgraph_e_responder,
        telefone,
        texto
    )

    # 3. Devolve 200 OK imediato para a Meta não reenviar por timeout
    return {"status": "aceito_para_processamento", "msg_id": msg_id}
