# arquivo: ex_cap03.py
from typing import TypedDict, Literal
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END

@tool
def calcular_frete_cep(cep: str) -> str:
    """Recebe o CEP (8 dígitos) e retorna o valor do frete em reais."""
    limpo = cep.replace("-", "").strip()
    if limpo.startswith("01"):
        return "Frete grátis (R$ 0,00)"
    return "Frete fixo: R$ 45,00"

@tool
def calcular_orcamento_exato(
    preco_unitario: float,
    quantidade: int,
    percentual_desconto: float = 0.0,
) -> str:
    """Calcula orçamento respeitando o teto comercial de 15%."""
    if percentual_desconto > 15.0:
        return "Negado: desconto acima do limite máximo de 15%."
    bruto = preco_unitario * quantidade
    final = bruto * (1.0 - (percentual_desconto / 100.0))
    return f"Total final: R$ {final:.2f}"

class EstadoRoteador(TypedDict):
    pergunta: str
    curta: bool
    resposta: str

def no_filtro_tamanho(estado: EstadoRoteador) -> dict:
    if len(estado["pergunta"].strip()) < 5:
        return {
            "curta": True,
            "resposta": "Pergunta muito curta. Detalhe seu pedido.",
        }
    return {"curta": False}

def no_atender(estado: EstadoRoteador) -> dict:
    return {"resposta": f"Processado: {estado['pergunta']}"}

def rota(estado: EstadoRoteador) -> Literal["fim", "atender"]:
    return "fim" if estado["curta"] else "atender"

g = StateGraph(EstadoRoteador)
g.add_node("filtro", no_filtro_tamanho)
g.add_node("atender", no_atender)
g.add_edge(START, "filtro")
g.add_conditional_edges(
    "filtro", rota, {"fim": END, "atender": "atender"}
)
g.add_edge("atender", END)
app = g.compile()

if __name__ == "__main__":
    assert "grátis" in calcular_frete_cep.invoke({"cep": "01001-000"})
    assert "Negado" in calcular_orcamento_exato.invoke(
        {
            "preco_unitario": 100.0,
            "quantidade": 2,
            "percentual_desconto": 20.0,
        }
    )
    r = app.invoke({"pergunta": "Oi", "curta": False, "resposta": ""})
    assert r["curta"] is True
    print("Cap 03 OK:", r["resposta"])
