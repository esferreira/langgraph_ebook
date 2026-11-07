# ====================================================================
# ARQUIVO: terminal_teste.py
# OBJETIVO: Testar o grafo localmente no terminal (Modo Laboratório).
# ====================================================================

from grafo import agente_atendimento

print("=== TESTE LOCAL NO TERMINAL (digite 'sair' para encerrar) ===")
nome = input("Qual é o seu nome? ")

while True:
    msg = input("\nDigite sua mensagem: ")
    if msg.lower() == "sair":
        break

    # Acionamos o grafo passando os valores iniciais da prancheta
    resultado = agente_atendimento.invoke({
        "nome_cliente": nome,
        "mensagem_original": msg,
        "categoria": "",
        "resposta_final": "",
    })

    print(f"\n[Setor Detectado]: {resultado['categoria']}")
    print(f"[Resposta]: {resultado['resposta_final']}")
