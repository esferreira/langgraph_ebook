# arquivo: ingestar_documentos.py
# Execute no terminal apenas quando atualizar os manuais da empresa!
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

if __name__ == "__main__":
    loader = PyPDFLoader("manual_oficial_da_empresa.pdf")
    paginas = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=150
    )
    pedacos = splitter.split_documents(paginas)

    # Cria e persiste os vetores no diretório local uma única vez
    Chroma.from_documents(
        documents=pedacos,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        persist_directory="./banco_vetorial_empresa",
    )
    print(f"Ingestão concluída: {len(pedacos)} chunks indexados.")
