# arquivo: ex_cap02.py
import operator
from typing import Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError

class EstadoRelatorio(TypedDict):
    pedido_negocio: str
    sql_gerado: str
    erro_validacao: str
    tentativas: int
    aprovado: bool
    historico_erros: Annotated[list[str], operator.add]

def no_gerador_sql(estado: EstadoRelatorio) -> dict:
    t = estado.get("tentativas", 0) + 1
    if t == 1:
        sql = "SELECT regiao, SUM(valor) FROM vendas GROUP BY regiao"
    elif t == 2:
        sql = (
            "SELECT regiao, SUM(valor) FROM vendas "
            "WHERE ano = 2026 GROUP BY regiao"
        )
    else:
        sql = (
            "SELECT filial, regiao, SUM(valor) FROM vendas "
            "WHERE ano = 2026 GROUP BY filial, regiao"
        )
    return {"sql_gerado": sql, "tentativas": t}

def no_auditor(estado: EstadoRelatorio) -> dict:
    sql = estado["sql_gerado"].lower()
    if "2026" not in sql:
        erro = "Faltou filtro do ano 2026."
        return {
            "aprovado": False,
            "erro_validacao": erro,
            "historico_erros": [erro],
        }
    if "filial" not in sql:
        erro = "Faltou coluna filial."
        return {
            "aprovado": False,
            "erro_validacao": erro,
            "historico_erros": [erro],
        }
    return {"aprovado": True, "erro_validacao": ""}

def decidir(
    estado: EstadoRelatorio,
) -> Literal["corrigir", "finalizar"]:
    if estado["aprovado"] or estado["tentativas"] >= 3:
        return "finalizar"
    return "corrigir"

b = StateGraph(EstadoRelatorio)
b.add_node("gerador", no_gerador_sql)
b.add_node("auditor", no_auditor)
b.add_edge(START, "gerador")
b.add_edge("gerador", "auditor")
b.add_conditional_edges(
    "auditor",
    decidir,
    {"corrigir": "gerador", "finalizar": END},
)
grafo = b.compile()

if __name__ == "__main__":
    res = grafo.invoke(
        {
            "pedido_negocio": "Vendas 2026 por filial",
            "sql_gerado": "",
            "erro_validacao": "",
            "tentativas": 0,
            "aprovado": False,
            "historico_erros": [],
        },
        config={"recursion_limit": 10},
    )
    assert res["aprovado"] is True and res["tentativas"] == 3
    assert len(res["historico_erros"]) == 2
    print("Cap 02 OK — erros acumulados:", res["historico_erros"])
