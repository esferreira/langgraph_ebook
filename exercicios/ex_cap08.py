# arquivo: ex_cap08.py
from langchain_core.tools import tool

BANCO_PEDIDOS_EX = {
    "PED-104": {
        "cliente": "Fernanda Costa",
        "produto": "Teclado Mecânico RGB",
        "valor": 420.00,
        "status": "Entregue",
    }
}

@tool
def consultar_prazo_entrega(cep: str) -> str:
    """Consulta o prazo de entrega em dias úteis pelo CEP informado."""
    limpo = cep.replace("-", "").strip()
    if limpo.startswith(("01", "02", "03", "04", "05")):
        return "Prazo estimado: 2 dias úteis (Capital SP)."
    return "Prazo estimado: 5 dias úteis."

@tool
def reembolsar_ped104(codigo: str) -> str:
    """Reembolsa automaticamente pedidos até R$ 500,00."""
    ped = BANCO_PEDIDOS_EX[codigo]
    if ped["valor"] <= 500.00:
        ped["status"] = "Cancelado e Reembolsado Automaticamente"
        return f"SUCESSO: {codigo} estornado ({ped['valor']:.2f})"
    return "Pendente"

FERRAMENTAS = [consultar_prazo_entrega, reembolsar_ped104]
MAPA_FERRAMENTAS = {f.name: f for f in FERRAMENTAS}

if __name__ == "__main__":
    assert "consultar_prazo_entrega" in MAPA_FERRAMENTAS
    r1 = MAPA_FERRAMENTAS["consultar_prazo_entrega"].invoke(
        {"cep": "01310-100"}
    )
    r2 = MAPA_FERRAMENTAS["reembolsar_ped104"].invoke(
        {"codigo": "PED-104"}
    )
    assert "2 dias" in r1 and "SUCESSO" in r2
    print("Cap 08 OK:", r1, "|", r2)
