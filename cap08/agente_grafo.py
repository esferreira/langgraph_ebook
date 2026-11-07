# Arquivo 2: agente_grafo.py
"""
Motor LangGraph com RAG, Ferramentas, Controle de Janela de Contexto
(trim_messages + count_tokens_approximately), SQLite (SqliteSaver)
e Pausa para Aprovação Humana (interrupt).
"""

import os
import sqlite3
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
# Para usar Ollama local gratuito, descomente a linha abaixo:
# from langchain_ollama import ChatOllama

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt

from banco_conhecimento import BANCO_DE_PEDIDOS, buscar_politicas_rag


# =====================================================================
# 1. DEFINIÇÃO DO ESTADO DO GRAFO (A "Prancheta" Compartilhada)
# =====================================================================
class EstadoAgente(TypedDict):
    messages: Annotated[list, add_messages]
    contexto_rag: str


# =====================================================================
# 2. DEFINIÇÃO DAS FERRAMENTAS (TOOLS) COM TRAVA HUMANA (INTERRUPT)
# =====================================================================
@tool
def consultar_status_pedido(codigo_pedido: str) -> str:
    """
    Consulta os detalhes, valor e status de entrega de um pedido
    pelo código (ex: PED-101). Operação de leitura idempotente.
    """
    codigo = codigo_pedido.strip().upper()
    pedido = BANCO_DE_PEDIDOS.get(codigo)
    if not pedido:
        return (
            f"Pedido {codigo} não encontrado. "
            "Códigos válidos de teste: PED-101, PED-102 e PED-103."
        )

    return (
        f"Dados do Pedido {codigo}: Cliente: {pedido['cliente']} | "
        f"Produto: {pedido['produto']} | "
        f"Valor: R$ {pedido['valor']:.2f} | "
        f"Status Atual: {pedido['status']}"
    )


@tool
def solicitar_reembolso_pedido(codigo_pedido: str, motivo: str) -> str:
    """
    Processa o cancelamento e reembolso (estorno) de um pedido
    informando o código e o motivo.
    """
    codigo = codigo_pedido.strip().upper()
    pedido = BANCO_DE_PEDIDOS.get(codigo)
    if not pedido:
        return f"Erro: Pedido {codigo} não existe no sistema."

    # Trava de idempotência: se já foi cancelado, não repete
    if "Cancelado" in pedido["status"]:
        return (
            f"Aviso: Pedido {codigo} já consta como "
            f"'{pedido['status']}'."
        )

    valor = pedido["valor"]

    # Alçada automática: até R$ 500 aprova sem pausa humana
    if valor <= 500.00:
        BANCO_DE_PEDIDOS[codigo]["status"] = (
            "Cancelado e Reembolsado Automaticamente"
        )
        return (
            f"SUCESSO: Como o valor de R$ {valor:.2f} está na alçada "
            f"automática (até R$ 500,00), o reembolso do {codigo} "
            f"({pedido['produto']}) foi aprovado e estornado."
        )

    # Acima de R$ 500,00: pausa o grafo com interrupt()
    decisao_gerente = interrupt(
        {
            "aviso": "APROVAÇÃO FINANCEIRA NECESSÁRIA",
            "codigo_pedido": codigo,
            "cliente": pedido["cliente"],
            "produto": pedido["produto"],
            "valor": valor,
            "motivo_cliente": motivo,
            "pergunta": (
                f"Autoriza o estorno de R$ {valor:.2f} "
                f"para o pedido {codigo}?"
            ),
        }
    )

    # Ao receber Command(resume=...), a função retoma a partir daqui
    if str(decisao_gerente).strip().lower() in [
        "aprovado",
        "sim",
        "autorizado",
    ]:
        BANCO_DE_PEDIDOS[codigo]["status"] = (
            "Cancelado e Reembolsado (Aprovado pela Gerência)"
        )
        return (
            f"APROVADO PELO GERENTE: O reembolso de R$ {valor:.2f} "
            f"referente ao pedido {codigo} foi autorizado pela "
            "gerência financeira e o estorno foi emitido."
        )
    else:
        return (
            f"NEGADO PELO GERENTE: O reembolso do pedido {codigo} "
            f"(R$ {valor:.2f}) não foi autorizado pela gerência. "
            f"Status informado: {decisao_gerente}."
        )


FERRAMENTAS = [consultar_status_pedido, solicitar_reembolso_pedido]
MAPA_FERRAMENTAS = {f.name: f for f in FERRAMENTAS}

# Modelo rápido padrão (intercambiável por qualquer modelo com tools)
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)
# Para Ollama local, comente a linha acima e descomente a linha abaixo:
# llm = ChatOllama(model="qwen2.5:7b", temperature=0.1)

llm_com_ferramentas = llm.bind_tools(FERRAMENTAS)


# =====================================================================
# 3. DEFINIÇÃO DOS NÓS DO GRAFO
# =====================================================================
def no_triagem_e_rag(state: EstadoAgente):
    """
    Nó 1: Lê a última mensagem e busca regras no Mini-RAG.
    """
    ultima_msg = state["messages"][-1].content
    documentos_relevantes = buscar_politicas_rag(ultima_msg)
    return {"contexto_rag": documentos_relevantes}


def no_agente_principal(state: EstadoAgente):
    """
    Nó 2: Controla o tamanho da Janela de Contexto em tokens reais
    (usando count_tokens_approximately), monta o System Prompt com RAG
    e invoca o modelo.
    """
    # IMPORTANTE: usamos token_counter=count_tokens_approximately para
    # medir tokens de verdade (se usássemos token_counter=len, o trim
    # contaria quantidade de mensagens em vez de tokens!).
    historico_aparado = trim_messages(
        state["messages"],
        max_tokens=1000,
        strategy="last",
        token_counter=count_tokens_approximately,
        include_system=False,
        allow_partial=False,
        start_on="human",
    )

    prompt_sistema = SystemMessage(
        content=(
            "Você é o assistente virtual da ElectroShop.\n"
            "Use as Políticas abaixo para dúvidas de regras:\n"
            f"--- POLÍTICAS OFICIAIS (RAG) ---\n"
            f"{state.get('contexto_rag', '')}\n"
            "--------------------------------\n"
            "INSTRUÇÕES:\n"
            "1. Se o cliente perguntar sobre um pedido (ex: PED-101), "
            "chame `consultar_status_pedido`.\n"
            "2. Se o cliente pedir reembolso, cancelamento ou estorno, "
            "chame `solicitar_reembolso_pedido`.\n"
            "3. Seja cordial, objetivo e responda em português."
        )
    )

    resposta_ia = llm_com_ferramentas.invoke(
        [prompt_sistema] + historico_aparado
    )
    return {"messages": [resposta_ia]}


def no_executar_ferramentas(state: EstadoAgente):
    """
    Nó 3: Executa as ferramentas solicitadas pelo modelo (e dispara o
    interrupt se o reembolso ultrapassar R$ 500,00).
    """
    ultima_mensagem_ia = state["messages"][-1]
    respostas_ferramentas = []

    for chamada in ultima_mensagem_ia.tool_calls:
        nome_ferramenta = chamada["name"]
        argumentos = chamada["args"]
        ferramenta_selecionada = MAPA_FERRAMENTAS[nome_ferramenta]

        resultado_texto = ferramenta_selecionada.invoke(argumentos)

        respostas_ferramentas.append(
            ToolMessage(
                content=str(resultado_texto),
                name=nome_ferramenta,
                tool_call_id=chamada["id"],
            )
        )

    return {"messages": respostas_ferramentas}


# =====================================================================
# 4. ARESTA CONDICIONAL E COMPILAÇÃO COM BANCO DE DADOS SQLITE
# =====================================================================
def decidir_proximo_passo(
    state: EstadoAgente,
) -> Literal["ferramentas", "__end__"]:
    ultima_msg = state["messages"][-1]
    if hasattr(ultima_msg, "tool_calls") and ultima_msg.tool_calls:
        return "ferramentas"
    return "__end__"


construtor = StateGraph(EstadoAgente)
construtor.add_node("triagem_rag", no_triagem_e_rag)
construtor.add_node("agente", no_agente_principal)
construtor.add_node("ferramentas", no_executar_ferramentas)

construtor.add_edge(START, "triagem_rag")
construtor.add_edge("triagem_rag", "agente")
construtor.add_conditional_edges("agente", decidir_proximo_passo)
construtor.add_edge("ferramentas", "agente")

# Permite configurar o caminho do SQLite via variável de ambiente
CAMINHO_BANCO = os.getenv(
    "CAMINHO_SQLITE", "memoria_electroshop.sqlite"
)
conexao_sqlite = sqlite3.connect(CAMINHO_BANCO, check_same_thread=False)
checkpointer_sqlite = SqliteSaver(conexao_sqlite)

grafo_electroshop = construtor.compile(checkpointer=checkpointer_sqlite)
# Alias semântico para importação em rotas de atendimento
grafo_atendimento = grafo_electroshop
