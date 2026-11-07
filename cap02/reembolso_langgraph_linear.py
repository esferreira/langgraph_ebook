# ====================================================================
# ARQUIVO: reembolso_langgraph_linear.py
# LANGGRAPH: Para o mesmo problema linear acima, escrevemos quase o
# triplo de código (Estado, Nós e Arestas) sem ganho real.
# ====================================================================

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END


class EstadoReembolso(TypedDict):
    cliente: str
    valor: float
    motivo: str
    status: str
    mensagem: str


def no_aprovar_auto(state: EstadoReembolso) -> dict:
    valor = state["valor"]
    cli = state["cliente"]
    return {
        "status": "aprovado_automatico",
        "mensagem": f"Reembolso de R$ {valor:.2f} ({cli}) aprovado.",
    }


def no_mandar_gerencia(state: EstadoReembolso) -> dict:
    valor = state["valor"]
    return {
        "status": "em_analise",
        "mensagem": f"Pedido de R$ {valor:.2f} enviado para análise.",
    }


def rota_valor(
    state: EstadoReembolso,
) -> Literal["aprovar", "gerencia"]:
    return "aprovar" if state["valor"] <= 100.0 else "gerencia"


builder = StateGraph(EstadoReembolso)
builder.add_node("aprovar", no_aprovar_auto)
builder.add_node("gerencia", no_mandar_gerencia)
builder.add_conditional_edges(START, rota_valor)
builder.add_edge("aprovar", END)
builder.add_edge("gerencia", END)
grafo_reembolso = builder.compile()
