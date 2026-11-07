# arquivo: solucao_01_trim_messages.py
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver

# 1. Configuramos o aparador de mensagens (Janela Deslizante).
# Com max_tokens=80, cabem apenas o SystemMessage (~20 tokens)
# e a pergunta curta de hoje (~15 tokens), cortando os antigos.
aparador_de_contexto = trim_messages(
    max_tokens=80,
    strategy="last",
    token_counter=count_tokens_approximately,
    include_system=True,
    allow_partial=False,
    start_on="human",
)


def no_assistente_com_janela_deslizante(state: MessagesState):
    # Passo A: Lemos todas as mensagens acumuladas no banco de dados
    msgs_banco = state["messages"]

    # Passo B: Cortamos apenas na variável local que vai ao LLM.
    # O banco NÃO é apagado; filtramos só o que o modelo lê agora.
    mensagens_para_llm = aparador_de_contexto.invoke(msgs_banco)

    print("\n--- RAIO-X DA JANELA DE CONTEXTO ---")
    print(f"Total salvo no Banco (State): {len(msgs_banco)}")
    print(f"Total enviado ao LLM agora  : {len(mensagens_para_llm)}")
    for m in mensagens_para_llm:
        print(f"   -> [{m.type.upper()}]: {m.content[:60]}")

    # Passo C: Em produção, chame llm.invoke(mensagens_para_llm)
    resposta = AIMessage(
        content="Funcionamos hoje das 08h às 18h em Salvador."
    )

    # Passo D: Retornamos a nova resposta para ser anexada ao banco
    return {"messages": [resposta]}


builder = StateGraph(MessagesState)
builder.add_node("assistente", no_assistente_com_janela_deslizante)
builder.add_edge(START, "assistente")
builder.add_edge("assistente", END)

app = builder.compile(checkpointer=InMemorySaver())

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "web_cliente_vip_01"}}

    # Simulamos o SystemMessage + 4 mensagens longas no histórico
    mensagens_iniciais = [
        SystemMessage(
            content="Você é Consultor da Loja X. Seja educado."
        ),
        HumanMessage(
            content=(
                "Oi, há 3 meses comprei uma geladeira grande de inox "
                "com entrega em Salvador. " * 3
            )
        ),
        AIMessage(
            content=(
                "Que ótimo! Espero que sua geladeira de inox esteja "
                "funcionando muito bem aí em Salvador. " * 3
            )
        ),
        HumanMessage(
            content=(
                "Mês passado também comprei um micro-ondas branco de "
                "30 litros na filial da Barra. " * 3
            )
        ),
        AIMessage(
            content=(
                "Perfeito! O micro-ondas de 30 litros é um excelente "
                "aparelho para o dia a dia. " * 3
            )
        ),
    ]
    app.invoke({"messages": mensagens_iniciais}, config=config)

    # Agora o cliente envia uma pergunta curta hoje:
    print("\n>>> CLIENTE ENVIA NOVA MENSAGEM HOJE <<<")
    pergunta_hoje = "Qual é o horário de funcionamento da loja hoje?"
    app.invoke(
        {"messages": [HumanMessage(content=pergunta_hoje)]},
        config=config,
    )
