# ====================================================================
# ARQUIVO: reembolso_python_puro.py
# PYTHON PURO: Para uma decisão linear sem loops nem pausas em banco,
# este código é mais curto, legível e dispensa o uso de LangGraph.
# ====================================================================


def analisar_reembolso_python_puro(
    cliente: str, valor: float, motivo: str
) -> dict:
    # Passo 1: Validação básica
    if valor <= 0:
        return {"status": "erro", "mensagem": "Valor inválido."}

    # Passo 2: Decisão simples com if/else (exemplo de triagem rápida)
    if valor <= 100.0:
        return {
            "status": "aprovado_automatico",
            "mensagem": (
                f"Reembolso de R$ {valor:.2f} para {cliente} "
                f"aprovado automaticamente."
            ),
        }
    else:
        return {
            "status": "em_analise",
            "mensagem": (
                f"Pedido de R$ {valor:.2f} ({motivo}) "
                f"enviado para análise."
            ),
        }


# Executando:
if __name__ == "__main__":
    res = analisar_reembolso_python_puro(
        "Maria", 85.0, "Produto veio riscado"
    )
    print(res)
