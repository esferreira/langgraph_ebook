"""
Suíte de testes de fumaça (pytest) dos exemplos e exercícios do livro
"LangGraph no Mundo Real" — Écio Soares Ferreira.

- Executa todos os exemplos determinísticos dos Capítulos 1 a 8 (sem LLM).
- Executa todos os 8 arquivos de gabarito do Apêndice D (ex_cap01.py .. ex_cap08.py).
- Exemplos que exigem LLM real são marcados com skip se OPENAI_API_KEY não estiver definida.
"""

import os
import subprocess
import sys
from pathlib import Path
import pytest

CODIGO_DIR = Path(__file__).resolve().parent.parent
BOOK_DIR = CODIGO_DIR.parent

TEM_CHAVE_OPENAI = bool(
    os.getenv("OPENAI_API_KEY", "").strip()
    and not os.getenv("OPENAI_API_KEY", "").startswith("sk-sua-")
)


def rodar_script(
    caminho_relativo: str,
    cwd: Path | None = None,
    stdin_text: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> str:
    script_path = CODIGO_DIR / caminho_relativo
    assert script_path.exists(), f"Arquivo não encontrado: {script_path}"
    pasta_exec = cwd or script_path.parent
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)
    res = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(pasta_exec),
        env=env,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert res.returncode == 0, (
        f"Falha em {caminho_relativo} (rc={res.returncode}):\n"
        f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    )
    return res.stdout


def test_smoke_ambiente():
    from importlib.metadata import version

    saida = rodar_script("teste_ambiente.py")
    assert f"LangGraph {version('langgraph')} pronto!" in saida


def test_cap01_grafo_e_api():
    saida = rodar_script(
        "cap01/terminal_teste.py",
        stdin_text="Mariana\nPreciso da segunda via do boleto\nsair\n",
    )
    assert "financeiro" in saida

    # Testa também a API FastAPI do Cap. 1 via TestClient
    sys.path.insert(0, str(CODIGO_DIR / "cap01"))
    try:
        from fastapi.testclient import TestClient
        import servidor_api

        client = TestClient(servidor_api.app)
        resp = client.post(
            "/atender",
            json={
                "nome_cliente": "Mariana",
                "mensagem": "Quero segunda via do boleto",
            },
        )
        assert resp.status_code == 200
        dados = resp.json()
        assert dados["setor_acionado"] == "financeiro"
    finally:
        sys.path.pop(0)


def test_cap02_if_else_e_ciclo():
    saida_puro = rodar_script("cap02/reembolso_python_puro.py")
    assert "aprovado_automatico" in saida_puro

    saida_ciclo = rodar_script("cap02/exemplo_ciclo_autocorrecao.py")
    assert "[AUD-9981]" in saida_ciclo and "aprovado" in saida_ciclo


def test_cap03_ferramentas_deterministicas():
    for arq in ("multi_llm_roteador.py", "agente_real_com_tools.py"):
        caminho = CODIGO_DIR / "cap03" / arq
        compile(caminho.read_text(encoding="utf-8"), str(caminho), "exec")


@pytest.mark.skipif(
    not TEM_CHAVE_OPENAI,
    reason="OPENAI_API_KEY não configurada para chamada de LLM em nuvem",
)
def test_cap03_execucao_com_llm():
    rodar_script("cap03/multi_llm_roteador.py")
    rodar_script("cap03/agente_real_com_tools.py")


def test_cap04_persistencia_sqlite_e_separacao_estado(tmp_path):
    saida_sqlite = rodar_script(
        "cap04/exemplo_01_persistencia_sqlite.py", cwd=tmp_path
    )
    assert "Total de mensagens salvas no disco: 4" in saida_sqlite

    saida_sep = rodar_script("cap04/solucao_03_separar_dados_brutos.py")
    assert "NF-2026-889" in saida_sep and "429,90" in saida_sep


def test_cap05_hitl_interrupt_e_hmac(tmp_path):
    saida_hitl = rodar_script(
        "cap05/sistema_producao_hitl_webhook.py",
        cwd=tmp_path,
        extra_env={"WEBHOOK_SECRET": "segredo-corporativo-32-bytes-123"},
    )
    assert "PAGO: PIX de R$ 5000.00 executado" in saida_hitl


def test_cap06_sintaxe_crag():
    for arq in ("chatbot_rag_agentico.py", "ingestar_documentos.py"):
        caminho = CODIGO_DIR / "cap06" / arq
        compile(caminho.read_text(encoding="utf-8"), str(caminho), "exec")


def test_cap07_sintaxe_servidores_multicanal():
    for arq in (
        "servidor_portal.py",
        "webhook_whatsapp_meta.py",
        "servidor_sms.py",
        "webhook_whatsapp_producao.py",
    ):
        caminho = CODIGO_DIR / "cap07" / arq
        compile(caminho.read_text(encoding="utf-8"), str(caminho), "exec")


def test_cap08_banco_conhecimento_e_ferramentas():
    sys.path.insert(0, str(CODIGO_DIR / "cap08"))
    try:
        import banco_conhecimento as bk

        trecho = bk.buscar_politicas_rag("Quero pedir reembolso")
        assert "POLÍTICA DE REEMBOLSO" in trecho

        ped = bk.BANCO_DE_PEDIDOS.get("PED-102")
        assert ped is not None and ped["valor"] == 4800.00
    finally:
        sys.path.pop(0)


@pytest.mark.parametrize(
    "arquivo_ex",
    [
        "exercicios/ex_cap01.py",
        "exercicios/ex_cap02.py",
        "exercicios/ex_cap03.py",
        "exercicios/ex_cap04.py",
        "exercicios/ex_cap05.py",
        "exercicios/ex_cap06.py",
        "exercicios/ex_cap07.py",
        "exercicios/ex_cap08.py",
    ],
)
def test_exercicios_apendice_d(arquivo_ex: str):
    saida = rodar_script(arquivo_ex)
    assert "OK" in saida
