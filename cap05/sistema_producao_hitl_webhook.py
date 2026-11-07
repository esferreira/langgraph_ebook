# arquivo: sistema_producao_hitl_webhook.py
import hashlib
import hmac
import html
import os
import secrets
import sqlite3
from typing import Literal
from typing_extensions import TypedDict
from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

from notificadores_reais import (
    enviar_alerta_whatsapp,
    enviar_alerta_telegram,
    enviar_alerta_email,
)


# 1. DEFINIÇÃO DO ESTADO DO GRAFO
class EstadoReembolso(TypedDict):
    pedido_id: str
    nome_cliente: str
    valor_reembolso: float
    motivo: str
    precisa_aprovacao_humana: bool
    token_aprovacao: str
    decisao_gerente: str
    status_final: str


# 2. OS NÓS DO GRAFO LANGGRAPH
def no_avaliar_risco(state: EstadoReembolso):
    """Ato 1: Verifica se o valor ultrapassa a alçada de R$ 500,00."""
    valor = state["valor_reembolso"]
    pid = state["pedido_id"]
    print(f"\n🔍 [Nó 1: Risco] Pedido #{pid} (R$ {valor:.2f})")

    if valor > 500.0:
        print("⚠️  Acima de R$ 500: exige aval do gerente.")
        return {
            "precisa_aprovacao_humana": True,
            "status_final": "AGUARDANDO_GERENTE",
        }

    print("✅ Até R$ 500,00: aprovação automática liberada.")
    return {
        "precisa_aprovacao_humana": False,
        "decisao_gerente": "SIM_AUTOMATICO",
    }


def no_notificar_gerente(state: EstadoReembolso):
    """
    Ato 2 (Parte A): Gera um token criptográfico de uso único e envia
    o alerta antes do nó de interrupt (evitando reenvio na retomada).
    """
    token_unico = secrets.token_urlsafe(16)
    resumo_alerta = (
        f"Cliente: {state['nome_cliente']}\n"
        f"Valor Solicitado: R$ {state['valor_reembolso']:.2f}\n"
        f"Motivo: {state['motivo']}"
    )
    thread_id = state["pedido_id"]

    enviar_alerta_whatsapp(
        numero_destino="5511999998888",
        mensagem=resumo_alerta,
        thread_id=thread_id,
        token_aprovacao=token_unico,
    )
    enviar_alerta_telegram(
        mensagem=resumo_alerta,
        thread_id=thread_id,
        token_aprovacao=token_unico,
    )
    enviar_alerta_email(
        email_gerente="gerente@suaempresa.com.br",
        mensagem=resumo_alerta,
        thread_id=thread_id,
        token_aprovacao=token_unico,
    )
    return {
        "token_aprovacao": token_unico,
        "status_final": "NOTIFICACAO_ENVIADA_AO_GERENTE",
    }


def no_congelar_e_aguardar_humano(state: EstadoReembolso):
    """
    Ato 2 (Parte B): Executa interrupt().
    Na 1ª passagem, grava o checkpoint no SQLite e retorna o invoke().
    Na 2ª passagem (Webhook/POST), reexecuta o nó do topo e
    interrupt() devolve a decisão do gerente!
    """
    print(
        f"⏸️  [Nó 3: Interrupt] Congelando processo "
        f"#{state['pedido_id']} no Banco de Dados..."
    )

    resposta_humana = interrupt(
        {
            "aguardando": "Aval Financeiro (Alçada > R$ 500,00)",
            "pedido_id": state["pedido_id"],
            "valor": state["valor_reembolso"],
        }
    )

    print(
        f"▶️  [Nó 3: Descongelado!] Decisão recebida: "
        f"'{resposta_humana}'"
    )
    return {
        "decisao_gerente": str(resposta_humana).strip().upper(),
        "token_aprovacao": "",  # Invalida o token após o uso!
    }


def no_processar_pagamento_ou_recusa(state: EstadoReembolso):
    """Ato 4 (Conclusão): Efetiva o PIX ou registra a recusa."""
    decisao = state.get("decisao_gerente", "NAO")
    pid = state["pedido_id"]
    cli = state["nome_cliente"]
    val = state["valor_reembolso"]

    if decisao in ("SIM", "S", "APROVAR", "SIM_AUTOMATICO"):
        msg = f"PIX de R$ {val:.2f} executado para {cli} (#{pid})."
        print(f"✅ [Nó 4: Financeiro] {msg}")
        return {"status_final": f"PAGO: {msg}"}

    msg = f"Reembolso do Pedido #{pid} ({cli}) recusado pelo gerente."
    print(f"❌ [Nó 4: Financeiro] {msg}")
    return {"status_final": f"RECUSADO: {msg}"}


# 3. ROTEAMENTO E COMPILAÇÃO COM SQLITE
def rota_pos_avaliacao(
    state: EstadoReembolso,
) -> Literal["notificar_gerente", "processar_final"]:
    if state["precisa_aprovacao_humana"]:
        return "notificar_gerente"
    return "processar_final"


builder = StateGraph(EstadoReembolso)
builder.add_node("avaliar_risco", no_avaliar_risco)
builder.add_node("notificar_gerente", no_notificar_gerente)
builder.add_node("aguardar_humano", no_congelar_e_aguardar_humano)
builder.add_node("processar_final", no_processar_pagamento_ou_recusa)

builder.add_edge(START, "avaliar_risco")
builder.add_conditional_edges("avaliar_risco", rota_pos_avaliacao)
builder.add_edge("notificar_gerente", "aguardar_humano")
builder.add_edge("aguardar_humano", "processar_final")
builder.add_edge("processar_final", END)

conexao_db = sqlite3.connect(
    "./reembolsos_producao.db", check_same_thread=False
)
checkpointer_db = SqliteSaver(conexao_db)
grafo_reembolso = builder.compile(checkpointer=checkpointer_db)


# 4. FUNÇÃO AUXILIAR DE VALIDAÇÃO E RETOMADA SEGURA
def validar_e_retomar_processo(
    thread_id: str, token_recebido: str, decisao: str
) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    estado_atual = grafo_reembolso.get_state(config)

    # 1. Verifica se o processo existe e está realmente pausado
    if not estado_atual.values or not estado_atual.next:
        raise HTTPException(
            status_code=409,
            detail="Nenhum processo pendente para este ID.",
        )

    # 2. Compara o token em tempo constante contra ataques de timing
    token_salvo = estado_atual.values.get("token_aprovacao", "")
    if not token_salvo or not hmac.compare_digest(
        token_recebido, token_salvo
    ):
        raise HTTPException(
            status_code=403,
            detail="Token de aprovação inválido ou já utilizado.",
        )

    # 3. Descongela o grafo com segurança
    resultado = grafo_reembolso.invoke(
        Command(resume=decisao), config=config
    )
    return resultado


# 5. SERVIDOR WEB FASTAPI
# Sem valor padrão: recusa subir se WEBHOOK_SECRET não existir
api = FastAPI(title="Servidor LangGraph HITL Seguro")
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]


class NovoPedidoRequest(BaseModel):
    pedido_id: str
    nome_cliente: str
    valor_reembolso: float
    motivo: str


class WebhookRespostaHumana(BaseModel):
    remetente: str
    pedido_id: str
    token: str
    texto_resposta: str


@api.post("/solicitar-reembolso")
def endpoint_solicitar_reembolso(req: NovoPedidoRequest):
    config = {"configurable": {"thread_id": req.pedido_id}}
    resultado = grafo_reembolso.invoke(
        {
            "pedido_id": req.pedido_id,
            "nome_cliente": req.nome_cliente,
            "valor_reembolso": req.valor_reembolso,
            "motivo": req.motivo,
        },
        config=config,
    )

    estado_atual = grafo_reembolso.get_state(config)
    if estado_atual.next:
        return {
            "situacao": "PAUSADO_AGUARDANDO_HUMANO",
            "proximo_no": estado_atual.next,
        }
    return {
        "situacao": "CONCLUIDO_AUTOMATICAMENTE",
        "status_final": resultado["status_final"],
    }


@api.get("/confirmar-reembolso", response_class=HTMLResponse)
def pagina_confirmacao_email(thread_id: str, token: str):
    """
    Rota GET segura: apenas renderiza a página HTML de confirmação.
    Scanners de e-mail que abrem links GET não acionam o PIX,
    e html.escape() impede XSS refletido nos parâmetros da URL.
    """
    tid_seguro = html.escape(thread_id, quote=True)
    tok_seguro = html.escape(token, quote=True)
    return f"""
    <html><body>
      <h3>Confirmar Decisão — Protocolo {tid_seguro}</h3>
      <form method="POST" action="/aprovar-via-link">
        <input type="hidden" name="thread_id" value="{tid_seguro}" />
        <input type="hidden" name="token" value="{tok_seguro}" />
        <button type="submit" name="decisao" value="SIM">
          ✅ Confirmar Aprovação
        </button>
        <button type="submit" name="decisao" value="NAO">
          ❌ Recusar Reembolso
        </button>
      </form>
    </body></html>
    """


@api.post("/aprovar-via-link")
def endpoint_confirmar_post(
    thread_id: str = Form(...),
    token: str = Form(...),
    decisao: str = Form(...),
):
    """Rota POST: valida o token de uso único e retoma o grafo."""
    resultado = validar_e_retomar_processo(thread_id, token, decisao)
    return {
        "situacao": "PROCESSO_FINALIZADO",
        "resultado_operacao": resultado["status_final"],
    }


@api.post("/webhook/resposta-celular")
async def endpoint_webhook_celular(
    request: Request,
    webhook: WebhookRespostaHumana,
    x_hub_signature_256: str = Header(default=""),
):
    """
    Rota de Webhook: valida a assinatura HMAC (X-Hub-Signature-256)
    enviada pelo provedor antes de retomar o grafo.
    """
    corpo_bruto = await request.body()
    assinatura_esperada = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), corpo_bruto, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        x_hub_signature_256, assinatura_esperada
    ):
        raise HTTPException(
            status_code=401, detail="Assinatura de webhook inválida."
        )

    resultado = validar_e_retomar_processo(
        webhook.pedido_id, webhook.token, webhook.texto_resposta
    )
    return {
        "situacao": "PROCESSO_RETOMADO_VIA_WEBHOOK",
        "status_final": resultado["status_final"],
    }


# 6. SIMULAÇÃO COMPLETA NO TERMINAL
if __name__ == "__main__":
    print("🚀 INICIANDO SIMULAÇÃO (4 ATOS DO HUMAN-IN-THE-LOOP)\n")

    id_do_processo = "pedido_482"
    config_processo = {"configurable": {"thread_id": id_do_processo}}

    print(">>> [14h00] Cliente solicita reembolso de R$ 5.000,00...")
    grafo_reembolso.invoke(
        {
            "pedido_id": id_do_processo,
            "nome_cliente": "João da Silva",
            "valor_reembolso": 5000.00,
            "motivo": "Produto chegou com a tela trincada.",
        },
        config=config_processo,
    )

    foto_do_banco = grafo_reembolso.get_state(config_processo)
    token_gerado = foto_do_banco.values["token_aprovacao"]
    print("\n📋 [Auditoria do Servidor às 14h01]:")
    print("   - A chamada invoke() terminou? SIM (worker liberado).")
    print(f"   - Nó aguardando no SQLite: {foto_do_banco.next}")

    print("\n⏳ ... 3 horas se passam. Gerente aprova no celular ...")
    print(">>> [17h15] Validando token e acordando o LangGraph:\n")

    resultado_pos_webhook = validar_e_retomar_processo(
        thread_id=id_do_processo,
        token_recebido=token_gerado,
        decisao="SIM",
    )

    print("\n🎉 [Resultado Final após o Webhook]:")
    print("  ", resultado_pos_webhook["status_final"])
