# arquivo: ex_cap05.py
import time
import sqlite3
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

class EstadoReembolso(TypedDict):
    pedido_id: str
    valor: float
    nivel_alcada: str
    criado_em_ts: float
    decisao_gerente: str
    status_final: str

def no_avaliar(state: EstadoReembolso) -> dict:
    v = state["valor"]
    if v <= 500.0:
        alcada = "automatico"
    elif v <= 10000.0:
        alcada = "supervisor"
    else:
        alcada = "diretor"
    return {"nivel_alcada": alcada, "criado_em_ts": time.time()}

def no_pausa(state: EstadoReembolso) -> dict:
    if state["nivel_alcada"] == "automatico":
        return {
            "decisao_gerente": "SIM",
            "status_final": "APROVADO_AUTO",
        }
    decisao = interrupt({"alcada_exigida": state["nivel_alcada"]})
    return {"decisao_gerente": str(decisao)}

def no_finalizar(state: EstadoReembolso) -> dict:
    dec = state["decisao_gerente"]
    alcada = state["nivel_alcada"]
    if dec.upper().startswith("SIM"):
        return {"status_final": f"PIX_EXECUTADO ({alcada})"}
    return {"status_final": f"RECUSADO ({dec})"}

def token_expirado(
    criado_em_ts: float, agora: float | None = None
) -> bool:
    ref = agora if agora is not None else time.time()
    return (ref - criado_em_ts) > 86400

b = StateGraph(EstadoReembolso)
b.add_node("avaliar", no_avaliar)
b.add_node("pausa", no_pausa)
b.add_node("finalizar", no_finalizar)
b.add_edge(START, "avaliar")
b.add_edge("avaliar", "pausa")
b.add_edge("pausa", "finalizar")
b.add_edge("finalizar", END)

conn = sqlite3.connect(":memory:", check_same_thread=False)
grafo = b.compile(checkpointer=SqliteSaver(conn))

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "ped_900"}}
    grafo.invoke(
        {
            "pedido_id": "ped_900",
            "valor": 15000.0,
            "nivel_alcada": "",
            "criado_em_ts": 0.0,
            "decisao_gerente": "",
            "status_final": "",
        },
        config=cfg,
    )
    st = grafo.get_state(cfg)
    assert st.values["nivel_alcada"] == "diretor"
    assert not token_expirado(st.values["criado_em_ts"])
    assert token_expirado(st.values["criado_em_ts"] - 90000)
    fim = grafo.invoke(
        Command(resume="NAO: Fora da garantia"), config=cfg
    )
    assert "Fora da garantia" in fim["status_final"]
    print("Cap 05 OK:", fim["status_final"])
