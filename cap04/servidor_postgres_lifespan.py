# arquivo: servidor_postgres_lifespan.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://usuario:senha@localhost:5432/banco_langgraph",
)

grafo_produçao = None


@asynccontextmanager
async def lifespan(app_fastapi: FastAPI):
    global grafo_produçao
    # Abre o pool de conexões que viverá durante a execução
    with ConnectionPool(
        conninfo=DB_URI,
        max_size=20,
        kwargs={"autocommit": True},
    ) as pool:
        checkpointer = PostgresSaver(pool)
        # Cria as tabelas de checkpoint no Postgres na 1ª execução
        checkpointer.setup()
        grafo_produçao = builder.compile(checkpointer=checkpointer)
        yield
    # Ao encerrar o servidor, o bloco `with` fecha o pool com segurança


api = FastAPI(lifespan=lifespan)
