# ====================================================================
# ARQUIVO: servidor_api.py
# OBJETIVO: Expor o grafo LangGraph através de uma API Web (FastAPI).
# ====================================================================

from fastapi import FastAPI
from pydantic import BaseModel
from grafo import agente_atendimento

# 1. Instanciamos a aplicação FastAPI
app = FastAPI(
    title="API do Agente LangGraph",
    description="Servidor back-end para Portal Web e integrações",
    version="1.0.0",
)


# 2. Esquema de validação do JSON de entrada (Pydantic)
class PacoteEntrada(BaseModel):
    nome_cliente: str
    mensagem: str
    origem: str = "portal_web"


# 3. Esquema do JSON de resposta
class PacoteSaida(BaseModel):
    setor_acionado: str
    resposta_para_o_cliente: str
    origem_atendida: str


# 4. Rota HTTP POST principal
@app.post("/atender", response_model=PacoteSaida)
def processar_mensagem_do_cliente(dados: PacoteEntrada):
    # Acionamos o grafo com os dados validados da requisição HTTP
    estado_final = agente_atendimento.invoke({
        "nome_cliente": dados.nome_cliente,
        "mensagem_original": dados.mensagem,
        "categoria": "",
        "resposta_final": "",
    })

    return PacoteSaida(
        setor_acionado=estado_final["categoria"],
        resposta_para_o_cliente=estado_final["resposta_final"],
        origem_atendida=dados.origem,
    )


# Rota de verificação de saúde do serviço (healthcheck)
@app.get("/status")
def verificar_saude():
    return {"status": "online", "motor": "LangGraph ativo"}
