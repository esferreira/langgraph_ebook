# arquivo: solucao_02_no_resumidor_removemessage.py
from typing import Literal
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    RemoveMessage,
)
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver


# 1. Herdamos de MessagesState (que já traz a chave `messages`)
# e adicionamos o campo `resumo` para guardar a ata compacta.
class EstadoComResumo(MessagesState):
    resumo: str


# 2. Nó principal de atendimento
def chamar_modelo(state: EstadoComResumo):
    resumo_atual = state.get("resumo", "")

    if resumo_atual:
        msg_sistema = SystemMessage(
            content=(
                "Você é um assistente prestativo. "
                f"Resumo anterior do cliente: {resumo_atual}"
            )
        )
        mensagens_para_llm = [msg_sistema] + state["messages"]
    else:
        mensagens_para_llm = state["messages"]

    print(
        f"[Nó Atendimento] Enviando {len(mensagens_para_llm)} "
        "mensagens ao LLM."
    )

    ultima_fala = state["messages"][-1].content
    resposta = AIMessage(
        content=f"Anotado: '{ultima_fala}'. Posso ajudar em algo mais?"
    )
    return {"messages": [resposta]}


# 3. Nó Resumidor (Summarization Node)
def resumir_conversa(state: EstadoComResumo):
    print("🧹 [Nó Resumidor] Compactando mensagens antigas...")
    resumo_existente = state.get("resumo", "")

    # Em produção com LLM real, limite também o tamanho do resumo:
    # prompt = (
    #     f"Resumo atual: {resumo_existente}\n"
    #     "Atualize o resumo incorporando as novas mensagens em "
    #     "no máximo 120 palavras, mantendo apenas fatos essenciais."
    # )
    textos_humanos = [
        m.content
        for m in state["messages"]
        if isinstance(m, HumanMessage)
    ]
    bloco_novo = "; ".join(textos_humanos)
    novo_resumo = (
        f"{resumo_existente} | {bloco_novo}".strip(" |")
    )[:300]  # Trava de segurança para o resumo não crescer sem limite

    # Apagamos todas as mensagens antigas, mantendo apenas as últimas 2
    mensagens_para_apagar = [
        RemoveMessage(id=m.id) for m in state["messages"][:-2]
    ]

    print(
        f"🧹 [Faxina Concluída] {len(mensagens_para_apagar)} "
        "mensagens antigas removidas da lista ativa."
    )
    print(f"📌 [Resumo Atualizado]: {novo_resumo}")

    return {
        "resumo": novo_resumo,
        "messages": mensagens_para_apagar,
    }


# 4. Aresta condicional: aciona a faxina quando passa de 6 mensagens
def decidir_se_resume(
    state: EstadoComResumo,
) -> Literal["resumir_conversa", "__end__"]:
    if len(state["messages"]) > 6:
        return "resumir_conversa"
    return END


workflow = StateGraph(EstadoComResumo)
workflow.add_node("conversar", chamar_modelo)
workflow.add_node("resumir_conversa", resumir_conversa)

workflow.add_edge(START, "conversar")
workflow.add_conditional_edges("conversar", decidir_se_resume)
workflow.add_edge("resumir_conversa", END)

app = workflow.compile(checkpointer=InMemorySaver())

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "web_resumo_123"}}

    frases_do_cliente = [
        "Oi, meu nome é Écio Soares.",
        "Eu moro em Salvador e tenho 2 cachorros.",
        "Meu orçamento máximo para o seguro é R$ 300 por mês.",
        "Prefiro pagamento no boleto bancário.",
    ]

    for frase in frases_do_cliente:
        print(f"\n>>> Cliente diz: {frase}")
        estado_final = app.invoke(
            {"messages": [HumanMessage(content=frase)]},
            config=config,
        )
        total_ativo = len(estado_final["messages"])
        print(f"Tamanho final de state['messages']: {total_ativo} msgs")
