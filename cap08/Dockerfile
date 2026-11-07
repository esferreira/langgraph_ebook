# Arquivo: Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instala primeiro as dependências fixadas (aproveita cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia apenas o código-fonte e o index.html
COPY banco_conhecimento.py agente_grafo.py /app/
COPY servidor.py index.html /app/

# Diretório dedicado para persistir o banco SQLite em volume
RUN mkdir -p /dados
ENV CAMINHO_SQLITE=/dados/memoria_electroshop.sqlite

EXPOSE 8000
CMD ["uvicorn", "servidor:app", "--host", "0.0.0.0", "--port", "8000"]
