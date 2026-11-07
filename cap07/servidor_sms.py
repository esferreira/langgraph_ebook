# Arquivo: servidor_sms.py
# Dependências necessárias:
# pip install fastapi uvicorn python-multipart twilio
# pip install langgraph langchain-openai

import os
from xml.sax.saxutils import escape
from typing import Annotated
from typing_extensions import TypedDict
from fastapi import FastAPI, Form, Request, Response, HTTPException
from twilio.request_validator import RequestValidator

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# =====================================================================
# 1. GRAFO LANGGRAPH OTIMIZADO PARA SMS (Respostas Curtas)
# =====================================================================
class EstadoSMS(TypedDict):
    messages: Annotated[list, add_messages]

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)

async def no_agente_sms(state: EstadoSMS):
    # No SMS, cada mensagem padrão no alfabeto GSM tem limite de
    # 160 caracteres. Instruímos o agente a ser conciso e sem Markdown.
    prompt_sistema_sms = SystemMessage(
        content=(
            "Você é o assistente da RápidoBR via SMS.\n"
            "REGRAS OBRIGATÓRIAS DE SMS:\n"
            "1. Responda em no máximo 150 caracteres.\n"
            "2. Não use formatação Markdown (sem *, # ou listas).\n"
            "3. Seja direto, claro e prestativo."
        )
    )
    mensagens = [prompt_sistema_sms] + state["messages"]
    resposta = await llm.ainvoke(mensagens)
    return {"messages": [resposta]}

construtor_sms = StateGraph(EstadoSMS)
construtor_sms.add_node("atendente_sms", no_agente_sms)
construtor_sms.add_edge(START, "atendente_sms")
construtor_sms.add_edge("atendente_sms", END)

memoria_sms = InMemorySaver()
grafo_sms = construtor_sms.compile(checkpointer=memoria_sms)


# =====================================================================
# 2. ENDPOINT FASTAPI QUE RECEBE E RESPONDE SMS (Padrão Twilio)
# =====================================================================
app = FastAPI(title="Gateway SMS + LangGraph")

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WEBHOOK_URL = os.getenv("TWILIO_PUBLIC_WEBHOOK_URL", "")
VALIDAR_ASSINATURA_TWILIO = (
    os.getenv("VALIDAR_TWILIO", "false").lower() == "true"
)

@app.post("/sms")
async def receber_e_responder_sms(
    request: Request,
    From: str = Form(...),  # Remetente (Ex: "+5511988887777")
    Body: str = Form(...)   # Texto do SMS enviado pelo usuário
):
    """
    Webhook para receber SMS via Twilio com X-Twilio-Signature
    e escape seguro de caracteres XML no TwiML.
    """
    # 1. Validação de segurança do Webhook (X-Twilio-Signature)
    if VALIDAR_ASSINATURA_TWILIO:
        validador = RequestValidator(TWILIO_AUTH_TOKEN)
        assinatura = request.headers.get("X-Twilio-Signature", "")
        form_dados = await request.form()
        # Atrás de proxy/ngrok, request.url chega como http://; use a
        # URL pública HTTPS configurada no painel da Twilio:
        url_publica = TWILIO_WEBHOOK_URL or str(request.url)
        if not validador.validate(
            url_publica, dict(form_dados), assinatura
        ):
            raise HTTPException(
                status_code=403,
                detail="Assinatura X-Twilio-Signature inválida",
            )

    print(f"[SMS RECEBIDO] De: {From} | Texto: {Body}")

    # 2. O número do celular prefixado com "sms_" vira o thread_id
    config_celular = {
        "configurable": {
            "thread_id": f"sms_{From}"
        }
    }

    # 3. Invoca o grafo LangGraph de forma assíncrona
    resultado = await grafo_sms.ainvoke(
        {"messages": [HumanMessage(content=Body)]},
        config=config_celular
    )
    resposta_curta_ia = resultado["messages"][-1].content

    print(f"[SMS ENVIADO] Para: {From} | Resposta: {resposta_curta_ia}")

    # 4. Escapamos &, < e > para nunca quebrar o parser XML da Twilio
    texto_xml_seguro = escape(resposta_curta_ia)

    twiml_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"    <Message>{texto_xml_seguro}</Message>\n"
        "</Response>"
    )

    return Response(content=twiml_xml, media_type="application/xml")
