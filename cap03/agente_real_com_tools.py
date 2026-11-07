# ====================================================================
# ARQUIVO: agente_real_com_tools.py
# OBJETIVO: Construir um Agente ReAct no LangGraph, demonstrando o
# ciclo entre o nó do modelo e o ToolNode (Execução Python).
# ====================================================================

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
# Para usar OpenAI: from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition


# --------------------------------------------------------------------
# PASSO 1: CRIAR AS FERRAMENTAS EM PYTHON PURO (@tool)
# A docstring e os nomes dos parâmetros orientam o LLM sobre quando
# chamar a função e em qual unidade passar cada argumento.
# --------------------------------------------------------------------
@tool
def buscar_preco_no_estoque(nome_produto: str) -> str:
    """
    Consulta o catálogo da loja para obter o preço unitário e a
    disponibilidade de um produto pelo nome. Use sempre que o cliente
    perguntar quanto custa algum item.
    """
    tabela_precos = {
        "notebook dell": 4500.00,
        "monitor lg": 1200.00,
        "mouse logitech": 250.00,
        "teclado mecanico": 480.00,
    }

    chave = nome_produto.lower().strip()
    for prod, preco in tabela_precos.items():
        if prod in chave or chave in prod:
            return (
                f"Produto encontrado: '{prod}' | "
                f"Preço unitário: R$ {preco:.2f} | Em estoque."
            )

    return f"Produto '{nome_produto}' não encontrado no estoque."


@tool
def calcular_orcamento_exato(
    preco_unitario: float,
    quantidade: int,
    percentual_desconto: float = 0.0,
) -> str:
    """
    Calcula o valor total de uma compra multiplicando preco_unitario
    por quantidade e aplicando percentual_desconto.
    IMPORTANTE: passe percentual_desconto na escala de 0 a 100
    (exemplo: passe 10.0 para representar 10% de desconto).
    """
    bruto = preco_unitario * quantidade
    desconto_reais = bruto * (percentual_desconto / 100.0)
    liquido = bruto - desconto_reais

    return (
        f"Cálculo oficial: Subtotal Bruto = R$ {bruto:.2f} | "
        f"Desconto ({percentual_desconto}%) = "
        f"R$ {desconto_reais:.2f} | "
        f"Total Final = R$ {liquido:.2f}"
    )


lista_de_ferramentas = [
    buscar_preco_no_estoque,
    calcular_orcamento_exato,
]

# --------------------------------------------------------------------
# PASSO 2: CONFIGURAR O MODELO E VINCULAR O CATÁLOGO DE FERRAMENTAS
# Nota: Para tool calling local confiável no Ollama, prefira modelos
# de 7B a 14B (como qwen2.5:7b ou llama3.1:8b) em vez de modelos 3B.
# --------------------------------------------------------------------
llm = ChatOllama(model="qwen2.5:7b", temperature=0)

# .bind_tools() registra as assinaturas e docstrings no modelo
llm_com_ferramentas = llm.bind_tools(lista_de_ferramentas)


# --------------------------------------------------------------------
# PASSO 3: DEFINIR OS DOIS NÓS DO GRAFO
# --------------------------------------------------------------------
def no_cerebro_agente(estado: MessagesState) -> dict:
    """
    Nó 1: Envia o histórico de mensagens ao modelo para que ele decida
    se solicita uma ferramenta (tool_calls) ou se responde ao cliente.
    """
    resposta_do_llm = llm_com_ferramentas.invoke(estado["messages"])
    return {"messages": [resposta_do_llm]}


# Nó 2: Executor do LangGraph que roda as funções pedidas
no_executor_ferramentas = ToolNode(lista_de_ferramentas)

# --------------------------------------------------------------------
# PASSO 4: MONTAR O GRAFO COM O CICLO ReAct
# --------------------------------------------------------------------
builder = StateGraph(MessagesState)

builder.add_node("agente", no_cerebro_agente)
builder.add_node("tools", no_executor_ferramentas)

builder.add_edge(START, "agente")

# Se a última AIMessage tiver tool_calls -> vai para "tools";
# caso contrário -> encerra em END.
builder.add_conditional_edges("agente", tools_condition)

# Fechamento do ciclo: após executar a ferramenta, retorna ao "agente"
builder.add_edge("tools", "agente")

meu_agente_vendas = builder.compile()


# --------------------------------------------------------------------
# PASSO 5: EXECUÇÃO COM PROTEÇÃO DE RECURSION_LIMIT
# --------------------------------------------------------------------
if __name__ == "__main__":
    pergunta = (
        "Olá! Qual o preço do Notebook Dell e quanto ficam "
        "3 unidades com 10% de desconto?"
    )
    print(f"CLIENTE: {pergunta}\n" + "=" * 64)

    for passo in meu_agente_vendas.stream(
        {"messages": [("user", pergunta)]},
        config={"recursion_limit": 10},
        stream_mode="values",
    ):
        ultima_msg = passo["messages"][-1]
        ultima_msg.pretty_print()
