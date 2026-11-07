# arquivo: chatbot_rag_agentico.py
import re
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

# =====================================================================
# 0. BASE DE CONHECIMENTO LOCAL (SIMULAÇÃO OFFLINE DE MANUAIS)
# =====================================================================
BASE_DOCUMENTOS_EMPRESA = [
    {
        "fonte": "Manual_Garantia_e_Defeitos_2026.pdf (Pág. 12)",
        "palavras_chave": [
            "defeito",
            "garantia",
            "conserto",
            "assistência",
            "técnica",
            "quebrou",
            "vício",
            "reparo",
        ],
        "conteudo": (
            "REGRA DE GARANTIA TÉCNICA: Caso o equipamento apresente "
            "defeito de fabricação dentro de 12 meses, o cliente tem "
            "direito a reparo gratuito em até 15 dias úteis ou troca."
        ),
    },
    {
        "fonte": "Politica_Reembolso_e_Arrependimento.pdf (Pág. 3)",
        "palavras_chave": [
            "devolução",
            "arrependimento",
            "reembolso",
            "estorno",
            "dinheiro",
            "cancelar",
            "prazo",
        ],
        "conteudo": (
            "DIREITO DE ARREPENDIMENTO: Compras feitas pelo site ou "
            "WhatsApp têm devolução em até 7 dias corridos após "
            "o recebimento, com reembolso via PIX em até 24 horas."
        ),
    },
    {
        "fonte": "Tabela_Planos_e_Precos_Comerciais.pdf (Pág. 1)",
        "palavras_chave": [
            "preço",
            "plano",
            "planos",
            "mensalidade",
            "valor",
            "custo",
            "assinatura",
            "ouro",
            "prata",
        ],
        "conteudo": (
            "TABELA DE PREÇOS: O Plano Prata custa R$ 99,90/mês "
            "(até 3 usuários). O Plano Ouro custa R$ 249,90/mês "
            "(usuários ilimitados + suporte no WhatsApp)."
        ),
    },
]


# =====================================================================
# 1. DEFINIÇÃO DO ESTADO DO CHATBOT + RAG AGÊNTICO
# =====================================================================
class EstadoChatbotRAG(TypedDict):
    messages: Annotated[list, add_messages]
    pergunta_atual: str
    termo_de_busca: str
    intencao: str  # "social" ou "consulta_rag"
    documentos_recuperados: list[str]
    documentos_sao_relevantes: bool
    tentativas_de_busca: int


# =====================================================================
# 2. OS NÓS DO GRAFO
# =====================================================================
PADRAO_SAUDACAO = re.compile(
    r"\b(oi|ol[aá]|bom dia|boa tarde|boa noite|"
    r"tudo bem|obrigad[oa]|valeu)\b"
)


def no_1_entender_pergunta_usuario(state: EstadoChatbotRAG):
    """
    Nó 1 (Triagem): Usa regex com fronteira de palavra (\\b) para que
    'oi' não case por engano com 'dois', 'noite' ou 'oito'.
    """
    ultima_msg = state["messages"][-1].content.strip()
    texto_lower = ultima_msg.lower()

    tem_saudacao = bool(PADRAO_SAUDACAO.search(texto_lower))
    eh_curta = len(texto_lower.split()) <= 4
    eh_apenas_social = tem_saudacao and eh_curta

    intencao = "social" if eh_apenas_social else "consulta_rag"
    print(
        f"\n🧠 [Nó 1: Triagem] '{ultima_msg}' -> "
        f"Intenção: [{intencao.upper()}]"
    )

    return {
        "pergunta_atual": ultima_msg,
        "termo_de_busca": ultima_msg,
        "intencao": intencao,
        "tentativas_de_busca": 0,
        "documentos_recuperados": [],
    }


def no_resposta_social_rapida(state: EstadoChatbotRAG):
    """Responde saudações sem acionar o banco vetorial."""
    print("💬 [Nó Social] Saudação respondida sem usar o RAG.")
    resposta = AIMessage(
        content="Olá! Sou o assistente da empresa. Como posso ajudar?"
    )
    return {"messages": [resposta]}


def no_2_buscar_documentos_rag(state: EstadoChatbotRAG):
    """Nó 2: Busca documentos usando `termo_de_busca`."""
    query = state["termo_de_busca"].lower()
    tentativa = state["tentativas_de_busca"] + 1
    print(
        f"🔎 [Nó 2: Busca RAG #{tentativa}] "
        f"Consultando base por: '{query}'"
    )

    docs_encontrados = []
    for doc in BASE_DOCUMENTOS_EMPRESA:
        if any(p in query for p in doc["palavras_chave"]):
            docs_encontrados.append(
                f"[{doc['fonte']}]: {doc['conteudo']}"
            )

    print(f"   -> Documentos recuperados: {len(docs_encontrados)}")
    return {
        "documentos_recuperados": docs_encontrados,
        "tentativas_de_busca": tentativa,
    }


def no_3_avaliar_qualidade_documentos(state: EstadoChatbotRAG):
    """
    Nó 3 (Juiz CRAG): Avalia se os documentos respondem à pergunta.
    NOTA: Nesta simulação sem API, checamos len(docs) > 0 porque o
    Nó 2 já filtra por palavras-chave. Veja a seguir a versão de
    10 linhas com LLM e with_structured_output para bancos vetoriais!
    """
    docs = state["documentos_recuperados"]

    if len(docs) > 0:
        print("✅ [Nó 3: Juiz CRAG] Documentos aprovados.")
        return {"documentos_sao_relevantes": True}

    print("⚠️  [Nó 3: Juiz CRAG] Nenhum trecho útil achado.")
    return {"documentos_sao_relevantes": False}


def no_reescrever_busca_inteligente(state: EstadoChatbotRAG):
    """Traduz gírias ou coloquialismos para termos técnicos."""
    pergunta_original = state["pergunta_atual"]
    print(
        f"🔄 [Nó Reescritor] Reescrevendo '{pergunta_original}' "
        "com termos técnicos..."
    )

    mapa_girias = {
        "pifou": "defeito garantia conserto assistência técnica",
        "parou": "defeito garantia reparo",
        "grana de volta": "reembolso devolução estorno",
        "caro": "preço plano valor mensalidade",
    }
    nova_query = pergunta_original.lower()
    for giria, termos_tecnicos in mapa_girias.items():
        if giria in nova_query:
            nova_query += " " + termos_tecnicos

    print(f"   -> Nova consulta gerada: '{nova_query}'")
    return {"termo_de_busca": nova_query}


def no_4_gerar_resposta_com_rag(state: EstadoChatbotRAG):
    """Nó 4: Redige a resposta com base nos trechos aprovados."""
    contexto_oficial = "\n".join(state["documentos_recuperados"])
    print("✍️  [Nó 4: Gerador RAG] Redigindo resposta final.")

    texto_resposta = (
        f"Consultei nossos manuais oficiais:\n"
        f"📄 {contexto_oficial}\n"
        f"Posso ajudar com mais alguma dúvida?"
    )
    return {"messages": [AIMessage(content=texto_resposta)]}


def no_5_transbordo_humano_honesto(state: EstadoChatbotRAG):
    """Nó 5: Se a regra não consta no manual, evita chutar."""
    print(
        "🛑 [Nó 5: Transbordo] Assunto ausente nos manuais. "
        "Encaminhando para atendente humano."
    )
    texto_honesto = (
        "Procurei em nossos manuais oficiais e não encontrei uma "
        "regra específica para essa questão. Estou transferindo seu "
        "atendimento para um especialista humano."
    )
    return {"messages": [AIMessage(content=texto_honesto)]}


# =====================================================================
# 3. FUNÇÕES DE ROTEAMENTO CONDICIONAL
# =====================================================================
def rota_apos_triagem(
    state: EstadoChatbotRAG,
) -> Literal["resposta_social", "buscar_rag"]:
    if state["intencao"] == "social":
        return "resposta_social"
    return "buscar_rag"


def rota_apos_avaliacao_rag(
    state: EstadoChatbotRAG,
) -> Literal["gerar_resposta", "reescrever_busca", "transferir_humano"]:
    if state["documentos_sao_relevantes"]:
        return "gerar_resposta"
    if state["tentativas_de_busca"] < 2:
        return "reescrever_busca"
    return "transferir_humano"


# =====================================================================
# 4. MONTAGEM E COMPILAÇÃO DO GRAFO
# =====================================================================
workflow = StateGraph(EstadoChatbotRAG)

workflow.add_node("triagem", no_1_entender_pergunta_usuario)
workflow.add_node("resposta_social", no_resposta_social_rapida)
workflow.add_node("buscar_rag", no_2_buscar_documentos_rag)
workflow.add_node("avaliar_rag", no_3_avaliar_qualidade_documentos)
workflow.add_node("reescrever_busca", no_reescrever_busca_inteligente)
workflow.add_node("gerar_resposta", no_4_gerar_resposta_com_rag)
workflow.add_node("transferir_humano", no_5_transbordo_humano_honesto)

workflow.add_edge(START, "triagem")
workflow.add_conditional_edges("triagem", rota_apos_triagem)
workflow.add_edge("resposta_social", END)

workflow.add_edge("buscar_rag", "avaliar_rag")
workflow.add_conditional_edges("avaliar_rag", rota_apos_avaliacao_rag)
workflow.add_edge("reescrever_busca", "buscar_rag")

workflow.add_edge("gerar_resposta", END)
workflow.add_edge("transferir_humano", END)

chatbot_rag_app = workflow.compile(checkpointer=InMemorySaver())

# =====================================================================
# 5. TESTANDO OS CENÁRIOS NO TERMINAL
# =====================================================================
if __name__ == "__main__":
    config_sessao = {"configurable": {"thread_id": "web_cliente_777"}}

    perguntas_teste = [
        # Cenário 1: Saudação social (pula o RAG)
        "Bom dia, tudo bem?",
        # Cenário 2: Pergunta curta com a palavra "dois" (contém "oi",
        # mas graças ao regex \b vai corretamente para consulta_rag!)
        "Tem dois planos?",
        # Cenário 3: Pergunta com gíria ("pifou") -> 1ª busca falha,
        # reescreve em loop e encontra o manual na 2ª tentativa!
        "Socorro, meu aparelho pifou ontem! Como funciona?",
        # Cenário 4: Assunto inexistente nos PDFs -> tenta, reescreve e
        # transfere para humano sem inventar resposta.
        "Vocês aceitam pagamento em Bitcoin ou Dogecoin?",
    ]

    for idx, pergunta in enumerate(perguntas_teste, 1):
        print("\n" + "=" * 70)
        print(f'TESTE #{idx} | CLIENTE: "{pergunta}"')
        print("=" * 70)

        estado_final = chatbot_rag_app.invoke(
            {"messages": [HumanMessage(content=pergunta)]},
            config=config_sessao,
        )

        print("\n🤖 RESPOSTA ENTREGUE:")
        print(estado_final["messages"][-1].content)
