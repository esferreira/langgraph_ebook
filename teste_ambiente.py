# arquivo: teste_ambiente.py
from importlib.metadata import version
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class EstadoTeste(TypedDict):
    status: str

v = version("langgraph")
g = StateGraph(EstadoTeste)
g.add_node("ok", lambda s: {"status": f"LangGraph {v} pronto!"})
g.add_edge(START, "ok")
g.add_edge("ok", END)
print(g.compile().invoke({"status": "iniciando"})["status"])
