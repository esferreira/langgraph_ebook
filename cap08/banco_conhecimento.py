# Arquivo 1: banco_conhecimento.py
"""
Módulo que simula a Base de Conhecimento (RAG) e o Banco de Pedidos
(ERP) da empresa fictícia ElectroShop.
"""

# 1. Documentos oficiais de políticas da empresa (Base RAG)
DOCUMENTOS_POLITICAS = [
    {
        "topico": "garantia defeito troca",
        "conteudo": (
            "POLÍTICA DE GARANTIA ELECTROSHOP: Todos os produtos "
            "possuem 90 dias de garantia legal e mais 9 meses de "
            "garantia contratual (total de 1 ano). Em caso de defeito "
            "nos primeiros 7 dias após o recebimento, fazemos a troca "
            "imediata ou o reembolso integral."
        )
    },
    {
        "topico": "frete entrega prazo envio",
        "conteudo": (
            "POLÍTICA DE FRETE E ENTREGA: O frete é grátis para "
            "compras acima de R$ 299,00 na região Sudeste. O prazo "
            "médio é de 2 dias úteis para capitais e até 6 dias "
            "úteis para o interior."
        )
    },
    {
        "topico": (
            "reembolso estorno cancelamento devolucao arrependimento"
        ),
        "conteudo": (
            "POLÍTICA DE REEMBOLSO E CANCELAMENTO: O cliente pode "
            "desistir da compra em até 7 dias após a entrega. "
            "Reembolsos até R$ 500,00 têm aprovação automática "
            "pelo agente virtual. Reembolsos acima de R$ 500,00 exigem "
            "aprovação obrigatória do Gerente Financeiro no sistema."
        )
    }
]

# 2. Banco de Dados Simulado de Pedidos (em memória para o piloto)
BANCO_DE_PEDIDOS = {
    "PED-101": {
        "cliente": "Carlos Silva",
        "produto": "Fone Bluetooth NoiseCancelling Pro",
        "valor": 350.00,
        "status": "Entregue há 3 dias",
        "pago": True
    },
    "PED-102": {
        "cliente": "Ana Souza",
        "produto": "Notebook Gamer UltraRTX 16GB",
        "valor": 4800.00,
        "status": "Em separação no estoque (Atrasado)",
        "pago": True
    },
    "PED-103": {
        "cliente": "Roberto Lima",
        "produto": "Monitor 27 Polegadas 4K",
        "valor": 1650.00,
        "status": "Em trânsito para a cidade do destinatário",
        "pago": True
    }
}


def buscar_politicas_rag(pergunta_usuario: str) -> str:
    """
    Mini-motor RAG local: recupera os documentos da empresa mais
    relevantes com base nos termos da pergunta do cliente.
    """
    pergunta_limpa = pergunta_usuario.lower()
    trechos_encontrados = []

    for doc in DOCUMENTOS_POLITICAS:
        palavras_chave = doc["topico"].split()
        if any(palavra in pergunta_limpa for palavra in palavras_chave):
            trechos_encontrados.append(doc["conteudo"])

    if not trechos_encontrados:
        return "\n".join([d["conteudo"] for d in DOCUMENTOS_POLITICAS])

    return "\n\n".join(trechos_encontrados)
