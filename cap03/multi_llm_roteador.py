# ====================================================================
# ARQUIVO: multi_llm_roteador.py
# OBJETIVO: Demonstrar o uso de dois modelos de categorias diferentes
# no mesmo grafo LangGraph:
# - Modelo 1 (Rápido/Econômico): Faz a triagem e atende casos simples.
# - Modelo 2 (Avançado): Acionado só em casos complexos.
# ====================================================================

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
# Para usar OpenAI: from langchain_openai import ChatOpenAI

# --------------------------------------------------------------------
# 1. INSTANCIANDO DOIS MODELOS DE CATEGORIAS DIFERENTES
# (Os nomes abaixo são intercambiáveis conforme a tabela)
# --------------------------------------------------------------------

# Categoria 1: Modelo rápido/econômico para triagem e respostas curtas
# (Em nuvem comercial, poderia ser "gpt-4.1-mini" ou "gemini-2.5-flash")
llm_rapido_economico = ChatOllama(model="qwen2.5:7b", temperature=0)

# Categoria 2: Modelo mais denso para análise técnica ou contratual
# (Em nuvem comercial, poderia ser "gpt-4.1" ou "claude-sonnet-4-5")
llm_especialista_forte = ChatOllama(
    model="qwen2.5:14b", temperature=0.2
)


# --------------------------------------------------------------------
# 2. DEFINIÇÃO DO ESTADO (A Prancheta)
# --------------------------------------------------------------------
class EstadoConsulta(TypedDict):
    pergunta_usuario: str
    nivel_complexidade: str   # 'simples' ou 'complexo'
    modelo_utilizado: str     # Registra qual categoria respondeu
    resposta: str


# --------------------------------------------------------------------
# 3. OS NÓS UTILIZANDO CADA CATEGORIA DE MODELO
# --------------------------------------------------------------------
def no_classificador_economico(estado: EstadoConsulta) -> dict:
    """
    Nó 1: Usa o modelo rápido/econômico para classificar se a dúvida
    é rotineira ou se exige análise aprofundada.
    """
    prompt = (
        "Classifique a pergunta abaixo respondendo apenas com uma "
        "palavra: 'SIMPLES' (saudação, horário, dúvida básica) ou "
        "'COMPLEXO' (análise contratual, arquitetura ou parecer).\n\n"
        f"Pergunta: {estado['pergunta_usuario']}\n"
        "Resposta (SIMPLES ou COMPLEXO):"
    )

    resultado_llm = llm_rapido_economico.invoke(prompt)
    texto = resultado_llm.content.strip().upper()

    nivel = "complexo" if "COMPLEXO" in texto else "simples"
    return {"nivel_complexidade": nivel}


def no_atendente_simples(estado: EstadoConsulta) -> dict:
    """
    Nó 2A: Em casos simples, o modelo econômico responde.
    """
    pergunta = estado["pergunta_usuario"]
    resposta_llm = llm_rapido_economico.invoke(
        f"Responda de forma objetiva e prestativa: {pergunta}"
    )
    return {
        "modelo_utilizado": "Modelo Rápido/Econômico (qwen2.5:7b)",
        "resposta": resposta_llm.content,
    }


def no_consultor_especialista(estado: EstadoConsulta) -> dict:
    """
    Nó 2B: Demanda complexa encaminhada ao modelo de maior capacidade.
    """
    pergunta = estado["pergunta_usuario"]
    resposta_llm = llm_especialista_forte.invoke(
        "Você é um consultor sênior. Analise com rigor técnico e "
        f"responda passo a passo:\n{pergunta}"
    )
    return {
        "modelo_utilizado": "Modelo Avançado (qwen2.5:14b)",
        "resposta": resposta_llm.content,
    }


# --------------------------------------------------------------------
# 4. ROTEAMENTO E COMPILAÇÃO DO GRAFO
# --------------------------------------------------------------------
def escolher_especialista(
    estado: EstadoConsulta,
) -> Literal["atendente_simples", "consultor_especialista"]:
    if estado["nivel_complexidade"] == "complexo":
        return "consultor_especialista"
    return "atendente_simples"


builder = StateGraph(EstadoConsulta)
builder.add_node("classificador", no_classificador_economico)
builder.add_node("atendente_simples", no_atendente_simples)
builder.add_node("consultor_especialista", no_consultor_especialista)

builder.add_edge(START, "classificador")
builder.add_conditional_edges("classificador", escolher_especialista)
builder.add_edge("atendente_simples", END)
builder.add_edge("consultor_especialista", END)

grafo_multi_llm = builder.compile()
