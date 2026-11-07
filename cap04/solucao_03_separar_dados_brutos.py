# arquivo: solucao_03_separar_dados_brutos.py
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# 1. O State guarda apenas o diálogo e referências enxutas!
# Nunca salvamos o XML/JSON bruto de 15 KB dentro do State para
# não inchar o banco de dados do Checkpointer a cada passo.
class EstadoEmpresarialLimpo(TypedDict):
    messages: Annotated[list, add_messages]
    ultima_fatura_id: str
    resumo_executivo_erp: str


# 2. Nó que consulta a API corporativa (Python puro, zero tokens)
def no_consultar_sistema_erp(state: EstadoEmpresarialLimpo):
    # Simulando retorno pesado de API (XML, logs de auditoria, etc.)
    # Essa variável é local: morre assim que a função termina!
    retorno_pesado_api = {
        "cliente_id": 99482,
        "xml_completo": "<xml>" + ("DADOS_DO_XML " * 800) + "</xml>",
        "logs_auditoria": ["log1", "log2", "log3"] * 200,
        "ultima_fatura": {
            "id": "NF-2026-889",
            "valor": "R$ 429,90",
            "vencimento": "15/11/2026",
            "status": "EM ABERTO",
        },
    }

    fatura = retorno_pesado_api["ultima_fatura"]
    resumo_limpo = (
        f"Nota {fatura['id']} | Valor: {fatura['valor']} | "
        f"Venc.: {fatura['vencimento']} | Status: {fatura['status']}"
    )

    tam_bruto = len(str(retorno_pesado_api))
    print("\n--- AUDITORIA DE MEMÓRIA E BANCO ---")
    print(f"JSON bruto da API (descartado): {tam_bruto} chars")
    print(f"Resumo salvo no State e Prompt: {len(resumo_limpo)} chars")

    return {
        "ultima_fatura_id": fatura["id"],
        "resumo_executivo_erp": resumo_limpo,
    }


# 3. Nó que aciona o LLM usando apenas o resumo enxuto
def no_responder_cliente(state: EstadoEmpresarialLimpo):
    fatos_erp = state["resumo_executivo_erp"]
    ultima_pergunta = state["messages"][-1].content

    prompt_enxuto = (
        f"Dados oficiais do sistema: [{fatos_erp}]\n"
        f"Pergunta do cliente: {ultima_pergunta}\n"
        "Responda de forma objetiva."
    )

    # Em produção: resposta = llm.invoke(prompt_enxuto)
    resposta = AIMessage(
        content=(
            f"Consultei o sistema (ref. {state['ultima_fatura_id']}): "
            f"fatura ({fatos_erp}) disponível para pagamento."
        )
    )
    return {"messages": [resposta]}


builder = StateGraph(EstadoEmpresarialLimpo)
builder.add_node("buscar_erp", no_consultar_sistema_erp)
builder.add_node("responder", no_responder_cliente)

builder.add_edge(START, "buscar_erp")
builder.add_edge("buscar_erp", "responder")
builder.add_edge("responder", END)

app = builder.compile()

if __name__ == "__main__":
    pergunta_nf = "Qual o valor e vencimento da minha última nota?"
    resultado = app.invoke(
        {"messages": [HumanMessage(content=pergunta_nf)]}
    )
    print("\nResposta Final:", resultado["messages"][-1].content)
