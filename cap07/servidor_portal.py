# Arquivo: servidor_portal.py
# Para instalar as dependências:
# pip install fastapi uvicorn langgraph langchain-openai pydantic

from typing import Annotated
from typing_extensions import TypedDict
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# =====================================================================
# 1. DEFINIÇÃO DO MOTOR LANGGRAPH (O "Cérebro" Único)
# =====================================================================
class EstadoAtendimento(TypedDict):
    messages: Annotated[list, add_messages]

# Modelo pequeno e rápido (intercambiável por qualquer outro provedor
# ou modelo local via ChatOllama)
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

async def no_atendente_portal(state: EstadoAtendimento):
    instrucao_sistema = SystemMessage(
        content=(
            "Você é o assistente virtual do Portal TechBrasil. "
            "Seja educado, direto e ajude o cliente com dúvidas "
            "sobre pedidos, segunda via de boleto e suporte técnico."
        )
    )
    mensagens_para_enviar = [instrucao_sistema] + state["messages"]
    # Chamada assíncrona (.ainvoke) para não bloquear o FastAPI
    resposta = await llm.ainvoke(mensagens_para_enviar)
    return {"messages": [resposta]}

construtor = StateGraph(EstadoAtendimento)
construtor.add_node("atendente", no_atendente_portal)
construtor.add_edge(START, "atendente")
construtor.add_edge("atendente", END)

# Em produção real, substitua InMemorySaver por AsyncSqliteSaver
# ou AsyncPostgresSaver
memoria = InMemorySaver()
grafo_empresa = construtor.compile(checkpointer=memoria)


# =====================================================================
# 2. CRIAÇÃO DA API WEB COM FASTAPI (A "Porta de Entrada")
# =====================================================================
app = FastAPI(title="API do Assistente LangGraph - Portal Corporativo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja ao domínio oficial
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequisicaoChat(BaseModel):
    mensagem: str

class RespostaChat(BaseModel):
    usuario_id: str
    resposta: str

# Simulação de autenticação de sessão no servidor (JWT)
def obter_usuario_da_sessao(
    x_token_sessao: str = Header(default="sessao_demo_ecio")
) -> str:
    """
    Em produção, decodifique aqui o token JWT ou cookie HttpOnly
    para descobrir quem é o usuário autenticado no servidor.
    """
    tabela_sessoes_ativas = {
        "sessao_demo_ecio": "cpf_123456",
        "sessao_demo_maria": "cpf_999888",
    }
    usuario_id = tabela_sessoes_ativas.get(x_token_sessao)
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Sessão inválida")
    return usuario_id

@app.post("/chat/web", response_model=RespostaChat)
async def endpoint_chat_portal(
    dados: RequisicaoChat,
    usuario_autenticado: str = Depends(obter_usuario_da_sessao),
):
    """
    Recebe a mensagem do Portal Web, vincula o thread_id à sessão
    autenticada no servidor e invoca o LangGraph de forma assíncrona.
    """
    # O thread_id nasce da sessão validada no backend (prevenindo IDOR)
    # e usa o prefixo padronizado "web_"
    config_sessao = {
        "configurable": {
            "thread_id": f"web_{usuario_autenticado}"
        }
    }

    # Usamos await .ainvoke() porque a rota é async def
    resultado = await grafo_empresa.ainvoke(
        {"messages": [HumanMessage(content=dados.mensagem)]},
        config=config_sessao
    )

    texto_resposta_ia = resultado["messages"][-1].content

    return RespostaChat(
        usuario_id=usuario_autenticado,
        resposta=texto_resposta_ia
    )

# Para rodar no terminal:
# uvicorn servidor_portal:app --reload --port 8000
