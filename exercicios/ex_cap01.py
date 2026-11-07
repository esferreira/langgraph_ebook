# arquivo: ex_cap01.py
from typing import TypedDict, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END

class EstadoAtendimento(TypedDict):
    mensagem_usuario: str
    setor_destino: str
    protocolo: str
    resposta_final: str

def no_triagem(estado: EstadoAtendimento) -> dict:
    txt = estado["mensagem_usuario"].lower()
    if any(p in txt for p in ["cancelar", "desistir", "encerrar"]):
        setor = "cancelamento"
    elif any(p in txt for p in ["boleto", "fatura", "nota", "pagar"]):
        setor = "financeiro"
    elif any(p in txt for p in ["erro", "caiu", "lento", "senha"]):
        setor = "suporte_tecnico"
    else:
        setor = "atendimento_geral"
    return {"setor_destino": setor, "protocolo": "PROT-001"}

def no_cancelamento(estado: EstadoAtendimento) -> dict:
    return {"resposta_final": "[Cancelamento]: Solicitação aberta."}

def no_financeiro(estado: EstadoAtendimento) -> dict:
    return {"resposta_final": "[Financeiro]: 2ª via emitida."}

def no_suporte(estado: EstadoAtendimento) -> dict:
    return {"resposta_final": "[Suporte]: Chamado técnico aberto."}

def no_geral(estado: EstadoAtendimento) -> dict:
    return {"resposta_final": "[Geral]: Como posso ajudar?"}

def decidir_caminho(
    estado: EstadoAtendimento,
) -> Literal["cancel", "fin", "sup", "ger"]:
    mapa = {
        "cancelamento": "cancel",
        "financeiro": "fin",
        "suporte_tecnico": "sup",
    }
    return mapa.get(estado["setor_destino"], "ger")

construtor = StateGraph(EstadoAtendimento)
construtor.add_node("triagem", no_triagem)
construtor.add_node("cancel", no_cancelamento)
construtor.add_node("fin", no_financeiro)
construtor.add_node("sup", no_suporte)
construtor.add_node("ger", no_geral)
construtor.add_edge(START, "triagem")
construtor.add_conditional_edges(
    "triagem",
    decidir_caminho,
    {
        "cancel": "cancel",
        "fin": "fin",
        "sup": "sup",
        "ger": "ger",
    },
)
for n in ("cancel", "fin", "sup", "ger"):
    construtor.add_edge(n, END)

agente = construtor.compile()
app = FastAPI()

class Pedido(BaseModel):
    mensagem: str

@app.post("/atender")
def atender(pedido: Pedido):
    if not pedido.mensagem.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia.")
    res = agente.invoke(
        {
            "mensagem_usuario": pedido.mensagem,
            "setor_destino": "",
            "protocolo": "",
            "resposta_final": "",
        }
    )
    return {
        "protocolo": res["protocolo"],
        "setor": res["setor_destino"],
        "resposta": res["resposta_final"],
    }

if __name__ == "__main__":
    r = atender(Pedido(mensagem="Quero cancelar minha assinatura"))
    assert r["setor"] == "cancelamento" and r["protocolo"] == "PROT-001"
    print("Cap 01 OK:", r)
