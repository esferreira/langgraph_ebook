# Código-Fonte Oficial — *LangGraph no Mundo Real*

**Autor:** Écio Soares Ferreira  
**Subtítulo:** *Como tirar agentes de IA do Jupyter e colocá-los em produção com Python, FastAPI, Bancos de Dados, WhatsApp, SMS e Portais Web*  
**Repositório oficial do livro:** https://github.com/esferreira/langgraph_ebook  
**Licença dos exemplos de código:** MIT (`LICENSE`)

Esta pasta contém todos os códigos-fonte dos Capítulos 1 a 8, o script de verificação de ambiente (`teste_ambiente.py`), as soluções completas e executáveis dos exercícios do **Apêndice D** (`exercicios/ex_cap01.py` a `ex_cap08.py`) e a suíte de testes automatizados (`tests/test_livro.py`).

Todos os arquivos de capítulos e exercícios são extraídos diretamente dos arquivos Markdown originais do livro pelo gerador editorial, garantindo **100% de identidade entre o código impresso na obra e o código desta pasta**.

---

## 1. Como Preparar o Ambiente

1. **Requisitos:** Python **3.11** ou superior.
2. **Crie e ative o ambiente virtual:**

```bash
python -m venv .venv
# No Windows (PowerShell ou CMD):
.venv\Scripts\activate
# No Linux ou macOS:
source .venv/bin/activate
```

3. **Instale as dependências fixadas:**

```bash
pip install -r requirements.txt
```

4. **Execute o teste de fumaça do ambiente:**

```bash
python teste_ambiente.py
```

---

## 2. Configurando o "Cérebro" de LLM (Opção A ou Opção B)

* **Capítulos 1 e 2** (bem como os exemplos determinísticos dos Capítulos 4, 5, 6 e todos os 8 arquivos em `exercicios/`) **rodam sem necessidade de LLM ou chave de API**.
* Para os exemplos que consultam um modelo de linguagem (Capítulos 3, 4, 6, 7 e 8), escolha uma das duas opções:

### Opção A — Gratuita e 100% Local (Ollama)
1. Instale o [Ollama](https://ollama.com) no seu sistema operacional.
2. Baixe o modelo recomendado para suporte a ferramentas (`@tool`):
   ```bash
   ollama pull qwen2.5:7b
   ollama list
   ```
3. Nos scripts que instanciam `ChatOpenAI`, substitua por `ChatOllama(model="qwen2.5:7b", temperature=0)` (conforme demonstrado no Capítulo 3).

### Opção B — Em Nuvem (OpenAI API)
Defina a variável `OPENAI_API_KEY` no seu terminal (ou copie `.env.example` para `.env`):

```bash
# Windows (PowerShell):
$env:OPENAI_API_KEY="sk-sua-chave-aqui"

# Linux / macOS:
export OPENAI_API_KEY="sk-sua-chave-aqui"
```

---

## 3. Estrutura de Pastas por Capítulo

| Pasta / Arquivo | Conteúdo Principal | Precisa de LLM? |
| :--- | :--- | :---: |
| `teste_ambiente.py` | Smoke test de 12 linhas da seção *"Antes de Começar"* | Não |
| `cap01/` | `grafo.py`, `terminal_teste.py`, `servidor_api.py` (Triagem com FastAPI) | Não |
| `cap02/` | `reembolso_python_puro.py`, `reembolso_langgraph_linear.py`, `exemplo_ciclo_autocorrecao.py` | Não |
| `cap03/` | `multi_llm_roteador.py`, `agente_real_com_tools.py` (ReAct e `@tool`) | Sim (A ou B) |
| `cap04/` | `exemplo_01_persistencia_sqlite.py`, `servidor_postgres_lifespan.py`, `solucao_01_trim_messages.py`, `solucao_02_no_resumidor_removemessage.py`, `solucao_03_separar_dados_brutos.py` | Parcial (`exemplo_01` e `solucao_03` rodam sem LLM) |
| `cap05/` | `notificadores_reais.py`, `sistema_producao_hitl_webhook.py` (`interrupt()`, `Command(resume=...)` e HMAC) | Não |
| `cap06/` | `chatbot_rag_agentico.py` (CRAG com citações), `ingestar_documentos.py` | Sim (A ou B) |
| `cap07/` | `servidor_portal.py`, `index.html`, `webhook_whatsapp_meta.py`, `servidor_sms.py`, `webhook_whatsapp_producao.py` | Sim (A ou B) |
| `cap08/` | Projeto Completo: `banco_conhecimento.py`, `agente_grafo.py`, `servidor.py`, `index.html`, `Dockerfile`, `.dockerignore`, `requirements.txt` | Sim (para o grafo completo; `banco_conhecimento.py` roda sem LLM) |
| `exercicios/` | Soluções completas do Apêndice D (`ex_cap01.py` a `ex_cap08.py`) | Não (100% determinísticos) |
| `tests/` | Suíte `pytest` (`test_livro.py`) que valida todos os capítulos e exercícios | Não (pula testes de LLM se não houver chave) |

---

## 4. Como Rodar a Suíte de Testes (`pytest`)

A partir da pasta `codigo/` (ou da raiz do livro), execute:

```bash
pytest -v
```

