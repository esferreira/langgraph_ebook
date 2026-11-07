# Arquivo 3: servidor.py
"""
Servidor Web FastAPI que expõe o grafo LangGraph em:
- GET  /          -> Interface Web (carrega index.html)
- POST /conversar -> Envia mensagem do cliente (checa se há pausa)
- POST /aprovar   -> Permite ao Gerente aprovar/rejeitar interrupt()
"""

import os
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agente_grafo import grafo_atendimento

app = FastAPI(title="CentralIA ElectroShop - Piloto LangGraph")

# Sem valor padrão: o servidor recusa subir se MANAGER_TOKEN faltar
TOKEN_GERENTE_ESPERADO = os.environ["MANAGER_TOKEN"]


class DadosConversa(BaseModel):
    thread_id: str
    mensagem: str


class DadosAprovacao(BaseModel):
    thread_id: str
    decisao: str  # "aprovado" ou "rejeitado"


def inspecionar_estado_da_sessao(config: dict) -> dict:
    """
    Verifica no Checkpointer SQLite se a conversa terminou normalmente
    ou se está pausada aguardando aprovação humana (interrupt).
    """
    estado_atual = grafo_atendimento.get_state(config)

    detalhes_interrupcao = None
    if estado_atual.tasks:
        for tarefa in estado_atual.tasks:
            if getattr(tarefa, "interrupts", None):
                detalhes_interrupcao = tarefa.interrupts[0].value
                break

    if detalhes_interrupcao:
        return {
            "status": "AGUARDANDO_APROVACAO_GERENTE",
            "resposta": (
                "⏳ [AGUARDANDO APROVAÇÃO]: Como o valor deste "
                "reembolso ultrapassa R$ 500,00, sua solicitação foi "
                "enviada para o Painel do Gerente Financeiro ao lado. "
                "Assim que ele aprovar ou rejeitar, concluiremos."
            ),
            "pendencia": detalhes_interrupcao,
        }

    mensagens = estado_atual.values.get("messages", [])
    ultima_resposta = (
        mensagens[-1].content if mensagens else "Sem resposta."
    )
    return {
        "status": "CONCLUIDO",
        "resposta": ultima_resposta,
        "pendencia": None,
    }


@app.post("/conversar")
def endpoint_conversar(dados: DadosConversa):
    config = {"configurable": {"thread_id": dados.thread_id}}

    # PROTEÇÃO DE FLUXO:
    # Antes de invocar o grafo com uma nova mensagem, verificamos se a
    # sessão já está pausada em um interrupt(). Se estiver, evitamos
    # empilhar HumanMessage após AIMessage com tool_calls abertas.
    estado_atual = grafo_atendimento.get_state(config)
    if estado_atual.next:
        status_pausado = inspecionar_estado_da_sessao(config)
        status_pausado["resposta"] = (
            "⏳ Sua solicitação anterior aguarda a decisão do "
            "Gerente Financeiro no painel ao lado. Por favor, aguarde "
            "a decisão antes de enviar novas mensagens."
        )
        return status_pausado

    # Invoca o grafo com limite explícito de recursão (disjuntor)
    config_execucao = {
        "configurable": {"thread_id": dados.thread_id},
        "recursion_limit": 10,
    }
    grafo_atendimento.invoke(
        {"messages": [HumanMessage(content=dados.mensagem)]},
        config=config_execucao,
    )

    return inspecionar_estado_da_sessao(config)


@app.post("/aprovar")
def endpoint_aprovar(
    dados: DadosAprovacao,
    x_manager_token: str = Header(default=""),
):
    # 1. Valida credencial do gerente antes de autorizar retomada
    if x_manager_token != TOKEN_GERENTE_ESPERADO:
        raise HTTPException(
            status_code=403,
            detail="Token de gerente inválido (X-Manager-Token).",
        )

    config = {"configurable": {"thread_id": dados.thread_id}}

    # 2. Verifica se realmente existe execução pausada nesta thread
    estado_atual = grafo_atendimento.get_state(config)
    if not estado_atual.next:
        raise HTTPException(
            status_code=409,
            detail="Não há solicitação pendente nesta sessão.",
        )

    # 3. Retoma o grafo a partir do ponto onde o interrupt() pausou
    grafo_atendimento.invoke(
        Command(resume=dados.decisao),
        config=config,
    )

    return inspecionar_estado_da_sessao(config)


@app.get("/", response_class=HTMLResponse)
def pagina_inicial_teste():
    caminho_html = Path(__file__).with_name("index.html")
    if caminho_html.exists():
        return caminho_html.read_text(encoding="utf-8")
    return "<h3>Salve o index.html do Apêndice C nesta pasta.</h3>"
