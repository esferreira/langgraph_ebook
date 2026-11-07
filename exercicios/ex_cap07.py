# arquivo: ex_cap07.py
import json
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

def gerar_twiml_seguro(mensagem: str) -> str:
    seguro = escape(mensagem)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{seguro}</Message></Response>"
    )

CACHE_MSG_TTL: dict[str, float] = {}

def msg_duplicada_ttl(
    msg_id: str, ttl_segundos: float = 3600.0
) -> bool:
    agora = time.time()
    expirados = [
        k
        for k, ts in CACHE_MSG_TTL.items()
        if agora - ts > ttl_segundos
    ]
    for k in expirados:
        del CACHE_MSG_TTL[k]
    if msg_id in CACHE_MSG_TTL:
        return True
    CACHE_MSG_TTL[msg_id] = agora
    return False

class EstadoStream(TypedDict):
    etapa: str

g = StateGraph(EstadoStream)
g.add_node("passo_1", lambda s: {"etapa": "Consultando ERP"})
g.add_node("passo_2", lambda s: {"etapa": "Concluído"})
g.add_edge(START, "passo_1")
g.add_edge("passo_1", "passo_2")
g.add_edge("passo_2", END)
grafo_s = g.compile()

def gerador_sse():
    for ev in grafo_s.stream({"etapa": ""}, stream_mode="updates"):
        yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

if __name__ == "__main__":
    xml_str = gerar_twiml_seguro("Promo P&G: > 10% & frete < R$ 20")
    ET.fromstring(xml_str)
    assert msg_duplicada_ttl("wamid.1") is False
    assert msg_duplicada_ttl("wamid.1") is True
    eventos = list(gerador_sse())
    assert len(eventos) == 2 and "passo_1" in eventos[0]
    print("Cap 07 OK:", len(eventos), "eventos SSE")
