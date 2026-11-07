# arquivo: ex_cap04.py
import re
import sqlite3
from typing import Annotated, Literal, TypedDict
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

def gerar_thread_id(
    canal: Literal["web", "wa", "sms"], identificador: str
) -> str:
    limpo = re.sub(r"\W+", "", identificador or "")
    if not limpo:
        raise ValueError("Identificador vazio.")
    return f"{canal}_{limpo}"

class EstadoTrim(TypedDict):
    messages: Annotated[list, add_messages]
    resumo_acumulado: str
    qtd_enviada_llm: int

def no_chat_controlado(state: EstadoTrim) -> dict:
    aparado = trim_messages(
        state["messages"],
        max_tokens=60,
        strategy="last",
        token_counter=count_tokens_approximately,
        include_system=True,
        start_on="human",
    )
    antigo = state.get("resumo_acumulado", "")
    resumo = (antigo + " | Novo turno")[-300:]
    return {
        "messages": [AIMessage(content="Registrado.")],
        "resumo_acumulado": resumo,
        "qtd_enviada_llm": len(aparado),
    }

b = StateGraph(EstadoTrim)
b.add_node("chat", no_chat_controlado)
b.add_edge(START, "chat")
b.add_edge("chat", END)

conn = sqlite3.connect(":memory:", check_same_thread=False)
app = b.compile(checkpointer=SqliteSaver(conn))

if __name__ == "__main__":
    tid = gerar_thread_id("wa", "+55 (11) 99999-1111")
    assert tid == "wa_5511999991111"
    cfg = {"configurable": {"thread_id": tid}}
    for i in range(6):
        msg = HumanMessage(content=f"Mensagem longa {i} " * 4)
        res = app.invoke({"messages": [msg]}, config=cfg)
    total_banco = len(app.get_state(cfg).values["messages"])
    assert total_banco == 12 and res["qtd_enviada_llm"] < total_banco
    assert len(res["resumo_acumulado"]) <= 300
    print(f"Cap 04 OK: db={total_banco}, trim={res['qtd_enviada_llm']}")
