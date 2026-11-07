# arquivo: ex_cap06.py
import re
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

DOCS = [
    {
        "fonte": "Politica_Frete_Expresso.pdf",
        "chaves": ["frete", "entrega", "prazo"],
        "texto": "Entrega expressa em 24h para capitais.",
    }
]

class EstadoCRAG(TypedDict):
    pergunta: str
    termo_busca: str
    rota: str
    docs: list[str]
    fontes: list[str]
    tentativas: int
    relevante: bool
    buscas_evitadas: int
    resposta: str

def no_triagem(s: EstadoCRAG) -> dict:
    txt = s["pergunta"].lower()
    if re.search(r"\b(oi|olá|bom dia)\b", txt):
        return {
            "rota": "social",
            "buscas_evitadas": s.get("buscas_evitadas", 0) + 1,
            "resposta": "Olá! Como posso ajudar?",
        }
    return {"rota": "rag", "termo_busca": txt, "tentativas": 0}

def no_buscar(s: EstadoCRAG) -> dict:
    t = s["termo_busca"]
    achados = [
        d for d in DOCS if any(k in t for k in d["chaves"])
    ]
    return {
        "docs": [d["texto"] for d in achados],
        "fontes": [d["fonte"] for d in achados],
        "tentativas": s["tentativas"] + 1,
    }

def no_juiz(s: EstadoCRAG) -> dict:
    return {"relevante": len(s["docs"]) > 0}

def no_reescrever(s: EstadoCRAG) -> dict:
    novo = s["termo_busca"].replace(
        "demora pra chegar", "frete entrega prazo"
    )
    return {"termo_busca": novo}

def no_responder(s: EstadoCRAG) -> dict:
    lista_f = ", ".join(s["fontes"])
    return {"resposta": f"{s['docs'][0]} (Fontes: {lista_f})"}

b = StateGraph(EstadoCRAG)
b.add_node("triagem", no_triagem)
b.add_node("buscar", no_buscar)
b.add_node("juiz", no_juiz)
b.add_node("reescrever", no_reescrever)
b.add_node("responder", no_responder)
b.add_edge(START, "triagem")
b.add_conditional_edges(
    "triagem",
    lambda s: "fim" if s["rota"] == "social" else "buscar",
    {"fim": END, "buscar": "buscar"},
)
b.add_edge("buscar", "juiz")
b.add_conditional_edges(
    "juiz",
    lambda s: "responder" if s["relevante"] else "reescrever",
    {"responder": "responder", "reescrever": "reescrever"},
)
b.add_edge("reescrever", "buscar")
b.add_edge("responder", END)
grafo = b.compile()

if __name__ == "__main__":
    r1 = grafo.invoke({"pergunta": "Bom dia!", "buscas_evitadas": 0})
    assert r1["buscas_evitadas"] == 1
    r2 = grafo.invoke(
        {"pergunta": "Comprei ontem, demora pra chegar?"}
    )
    assert "Politica_Frete_Expresso.pdf" in r2["resposta"]
    print("Cap 06 OK:", r2["resposta"])
