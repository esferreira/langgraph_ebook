# arquivo: exemplo_01_persistencia_sqlite.py
import sqlite3
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage, AIMessage


# 1. Definimos a estrutura da "Prancheta do Cliente" (State).
# O Annotated[list, add_messages] instrui o LangGraph a adicionar
# novas mensagens ao final da lista (APPEND) em vez de sobrescrevê-la.
class EstadoAtendimento(TypedDict):
    messages: Annotated[list, add_messages]
    nome_cliente: str


# 2. Criamos um nó simples (simulando um LLM para execução sem chave,
# podendo ser substituído por llm.invoke(state["messages"])).
def no_atendente(state: EstadoAtendimento):
    historico = state["messages"]
    ultima_msg = historico[-1].content
    total_acumulado = len(historico)

    resposta_texto = (
        f"[Memória ativa: {total_acumulado} msgs na pasta] "
        f"Recebi: '{ultima_msg}'."
    )
    return {"messages": [AIMessage(content=resposta_texto)]}


# 3. Construímos a estrutura do grafo
builder = StateGraph(EstadoAtendimento)
builder.add_node("atendente", no_atendente)
builder.add_edge(START, "atendente")
builder.add_edge("atendente", END)

# 4. Conectamos ao arquivo SQLite local "./memoria_clientes.db"
conexao_sqlite = sqlite3.connect(
    "./memoria_clientes.db", check_same_thread=False
)
checkpointer_banco = SqliteSaver(conexao_sqlite)

app = builder.compile(checkpointer=checkpointer_banco)

if __name__ == "__main__":
    # Etiqueta do Cliente 1 (prefixo wa_ + telefone)
    config_cliente_1 = {
        "configurable": {"thread_id": "wa_5511999991111"}
    }
    # Etiqueta do Cliente 2
    config_cliente_2 = {
        "configurable": {"thread_id": "wa_5521988882222"}
    }

    print("--- TURNO 1: Cliente 1 manda mensagem ---")
    msg_ecio = "Oi, sou o Écio de Salvador e quero meu saldo."
    res1 = app.invoke(
        {"messages": [HumanMessage(content=msg_ecio)]},
        config=config_cliente_1,
    )
    print("Agente -> Cliente 1:", res1["messages"][-1].content)

    print("\n--- TURNO 2: Cliente 1 manda outra mensagem ---")
    msg_cpf = "Meu CPF é 123.456.789-00."
    res2 = app.invoke(
        {"messages": [HumanMessage(content=msg_cpf)]},
        config=config_cliente_1,
    )
    print("Agente -> Cliente 1:", res2["messages"][-1].content)

    print("\n--- TURNO 3: Cliente 2 conversa em paralelo ---")
    res3 = app.invoke(
        {
            "messages": [
                HumanMessage(content="Olá, sou Maria. Quero ajuda.")
            ]
        },
        config=config_cliente_2,
    )
    print("Agente -> Cliente 2:", res3["messages"][-1].content)

    # Inspecionando o que ficou gravado no SQLite para o Cliente 1
    estado_salvo = app.get_state(config_cliente_1)
    msgs_salvas = estado_salvo.values["messages"]
    print("\n=======================================================")
    print("AUDITORIA DO BANCO (thread_id: wa_5511999991111)")
    print(f"Total de mensagens salvas no disco: {len(msgs_salvas)}")
    for idx, msg in enumerate(msgs_salvas, 1):
        tipo = "HUMANO" if isinstance(msg, HumanMessage) else "IA    "
        print(f"  {idx}. [{tipo}]: {msg.content}")
