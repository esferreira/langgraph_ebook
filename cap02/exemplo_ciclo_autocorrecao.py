# ====================================================================
# ARQUIVO: exemplo_ciclo_autocorrecao.py
# OBJETIVO: Demonstrar um ciclo (loop) controlado no LangGraph, onde
# um nó audita o resultado do nó anterior e solicita correção.
# ====================================================================

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END


# 1. A Prancheta (Estado) armazena o rascunho, a crítica e o contador
class EstadoRelatorio(TypedDict):
    dados_brutos: str
    rascunho_relatorio: str
    critica_auditoria: str
    tentativas: int
    aprovado: bool


# 2. NÓ 1: O Redator (Gera ou corrige o relatório lendo a crítica)
def no_redator(estado: EstadoRelatorio) -> dict:
    tentativa_atual = estado.get("tentativas", 0) + 1
    critica = estado.get("critica_auditoria", "")

    print(f"\n-> [Nó Redator] Tentativa nº {tentativa_atual}")

    # Simulando um gerador que omite a tag na 1ª tentativa e corrige
    # na 2ª tentativa após ler a crítica do auditor na prancheta:
    if tentativa_atual == 1 and not critica:
        texto_gerado = f"Resumo executivo: {estado['dados_brutos']}."
    else:
        print(f"   (Redator leu a crítica: '{critica}')")
        texto_gerado = f"[AUD-9981] Resumo: {estado['dados_brutos']}."

    return {
        "rascunho_relatorio": texto_gerado,
        "tentativas": tentativa_atual,
    }


# 3. NÓ 2: Auditor de Qualidade (Validação em Python puro)
def no_auditor_qualidade(estado: EstadoRelatorio) -> dict:
    texto = estado["rascunho_relatorio"]
    print(f"-> [Nó Auditor] Conferindo texto: '{texto}'")

    # Regra 1: Exige prefixo de auditoria [AUD-
    if "[AUD-" not in texto:
        return {
            "aprovado": False,
            "critica_auditoria": (
                "REPROVADO: Faltou o código '[AUD-XXXX]' no início."
            ),
        }

    # Regra 2: Limite máximo de 200 caracteres
    if len(texto) > 200:
        tam = len(texto)
        return {
            "aprovado": False,
            "critica_auditoria": (
                f"REPROVADO: Texto longo ({tam} chars). Máximo: 200."
            ),
        }

    print("   [Auditor]: Regras atendidas. Relatório aprovado.")
    return {
        "aprovado": True,
        "critica_auditoria": "",
    }


# 4. ARESTA CONDICIONAL (Decide se encerra ou retorna ao Redator)
def decidir_se_volta_ou_termina(
    estado: EstadoRelatorio,
) -> Literal["refazer_no_redator", "finalizar"]:
    if estado["aprovado"]:
        return "finalizar"

    # Trava explícita de negócio no Estado: máximo de 3 tentativas
    if estado["tentativas"] >= 3:
        print("   [Alerta]: Limite de 3 tentativas atingido.")
        return "finalizar"

    return "refazer_no_redator"


# 5. MONTAGEM DO GRAFO COM CICLO
builder = StateGraph(EstadoRelatorio)

builder.add_node("redator", no_redator)
builder.add_node("auditor", no_auditor_qualidade)

builder.add_edge(START, "redator")
builder.add_edge("redator", "auditor")

# Saindo de "auditor", retorna para "redator" (ciclo) ou vai para END
builder.add_conditional_edges(
    "auditor",
    decidir_se_volta_ou_termina,
    {
        "refazer_no_redator": "redator",
        "finalizar": END,
    },
)

grafo_com_ciclo = builder.compile()

# Executando o teste com proteção explícita de recursion_limit:
if __name__ == "__main__":
    resultado_final = grafo_com_ciclo.invoke(
        {
            "dados_brutos": "Faturamento subiu 18% na filial Sul",
            "rascunho_relatorio": "",
            "critica_auditoria": "",
            "tentativas": 0,
            "aprovado": False,
        },
        config={"recursion_limit": 10},
    )

    print("\n" + "=" * 56)
    tentativas = resultado_final["tentativas"]
    print(f"RESULTADO ENTREGUE APÓS {tentativas} TENTATIVA(S):")
    print(resultado_final["rascunho_relatorio"])
    print("=" * 56)
