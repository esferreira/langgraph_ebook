# ====================================================================
# ARQUIVO: grafo.py
# OBJETIVO: Definir o fluxo (Estado, Nós e Arestas) do atendimento.
# Este módulo não interage diretamente com tela nem rede; ele é
# importado pelo script de terminal ou pelo servidor FastAPI.
# ====================================================================

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END


# 1. DEFINIÇÃO DO ESTADO (A "Prancheta" que percorre os nós)
# Cada função (Nó) recebe este dicionário tipado e devolve apenas
# os campos que deseja atualizar.
class EstadoAtendimento(TypedDict):
    nome_cliente: str       # Nome de quem enviou a mensagem
    mensagem_original: str  # Texto enviado pelo usuário
    categoria: str          # 'financeiro', 'tecnico' ou 'geral'
    resposta_final: str     # Resposta preparada para o cliente


# 2. DEFINIÇÃO DOS NÓS (Funções Python que usam a prancheta)

def no_triagem(estado: EstadoAtendimento) -> dict:
    """
    Nó 1: Analisa a mensagem do cliente e classifica o setor.
    (No Capítulo 3 faremos isso com LLM; aqui usamos Python puro).
    """
    texto = estado["mensagem_original"].lower()

    palavras_fin = ["boleto", "fatura", "pagamento", "pix", "nota"]
    palavras_tec = ["erro", "travou", "bug", "lento", "senha"]

    if any(p in texto for p in palavras_fin):
        setor_escolhido = "financeiro"
    elif any(p in texto for p in palavras_tec):
        setor_escolhido = "tecnico"
    else:
        setor_escolhido = "geral"

    # Retornamos apenas o campo que será atualizado no Estado
    return {"categoria": setor_escolhido}


def no_setor_financeiro(estado: EstadoAtendimento) -> dict:
    """Nó 2A: Trata solicitações financeiras."""
    cliente = estado["nome_cliente"]
    resposta = (
        f"Olá, {cliente}. Identifiquei que sua solicitação é do "
        f"setor financeiro. Sua 2ª via de boleto/PIX já está "
        f"disponível na área do cliente."
    )
    return {"resposta_final": resposta}


def no_setor_tecnico(estado: EstadoAtendimento) -> dict:
    """Nó 2B: Trata chamados de suporte técnico."""
    cliente = estado["nome_cliente"]
    msg = estado["mensagem_original"]
    resposta = (
        f"Olá, {cliente}. Aqui é do suporte técnico. "
        f"Registrei o chamado sobre: '{msg}'. "
        f"Iniciamos a verificação automática da sua conta."
    )
    return {"resposta_final": resposta}


def no_setor_geral(estado: EstadoAtendimento) -> dict:
    """Nó 2C: Trata dúvidas comerciais e gerais."""
    cliente = estado["nome_cliente"]
    resposta = (
        f"Olá, {cliente}. Bem-vindo ao atendimento geral. "
        f"Recebemos sua mensagem e responderemos em instantes."
    )
    return {"resposta_final": resposta}


# 3. FUNÇÃO ROTEADORA (Aresta Condicional / equivalente ao CASE WHEN)
# Lê o campo 'categoria' preenchido na prancheta pelo Nó de Triagem
# e retorna o nome exato do próximo nó a ser executado.
def decidir_proximo_no(
    estado: EstadoAtendimento,
) -> Literal["no_financeiro", "no_tecnico", "no_geral"]:
    categoria_atual = estado["categoria"]

    if categoria_atual == "financeiro":
        return "no_financeiro"
    elif categoria_atual == "tecnico":
        return "no_tecnico"
    else:
        return "no_geral"


# 4. MONTAGEM DO GRAFO
construtor = StateGraph(EstadoAtendimento)

# Registramos os nós associando um nome a cada função Python
construtor.add_node("triagem", no_triagem)
construtor.add_node("no_financeiro", no_setor_financeiro)
construtor.add_node("no_tecnico", no_setor_tecnico)
construtor.add_node("no_geral", no_setor_geral)

# Conectamos a entrada (START) ao nó inicial ("triagem")
construtor.add_edge(START, "triagem")

# A partir de "triagem", a função roteadora decide o destino
construtor.add_conditional_edges("triagem", decidir_proximo_no)

# Todos os setores encerram o fluxo no marcador END
construtor.add_edge("no_financeiro", END)
construtor.add_edge("no_tecnico", END)
construtor.add_edge("no_geral", END)

# 5. COMPILAÇÃO DO GRAFO
# Variável exportada para ser importada por outros módulos
agente_atendimento = construtor.compile()
