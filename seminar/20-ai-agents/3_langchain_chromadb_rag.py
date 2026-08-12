"""
Showcase 3 — LangChain + ChromaDB: база профилей людей (write + search = RAG)
============================================================================
1. Пишем профили людей в ChromaDB (эмбеддинги OpenAI).
2. Ищем нужного человека по смыслу (similarity search).
3. LLM отвечает на вопрос, опираясь ТОЛЬКО на найденные профили.
"""
import os
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()
MODEL = os.getenv("GENERATOR_MODEL", "gpt-5.6-terra")

PROFILES = [
    {"name": "Арман Сулейменов", "bio": "Основатель школы программирования nFactorial в Алматы. Выпускник Purdue, финалист ACM ICPC, основатель Zero To One Labs."},
    {"name": "Ada Lovelace", "bio": "Первый в истории программист. Написала алгоритм для аналитической машины Чарльза Бэббиджа."},
    {"name": "Linus Torvalds", "bio": "Создатель ядра Linux и системы контроля версий Git. Родился в Финляндии."},
    {"name": "Guido van Rossum", "bio": "Создатель языка программирования Python. Работал в Google и Dropbox."},
    {"name": "Grace Hopper", "bio": "Пионер программирования, создатель компилятора и языка COBOL. Контр-адмирал ВМС США."},
]

store = Chroma(embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"))


def write(profiles: list[dict]):
    store.add_texts(
        texts=[f"{p['name']}: {p['bio']}" for p in profiles],
        metadatas=[{"name": p["name"]} for p in profiles],
    )
    print(f"✍️  записано профилей: {len(profiles)}")


def search(query: str, k: int = 2) -> list[str]:
    hits = store.similarity_search(query, k=k)
    print(f"🔎 найдено по запросу «{query}»:")
    for h in hits:
        print(f"   - {h.page_content}")
    return [h.page_content for h in hits]


def answer(query: str) -> str:
    context = "\n".join(search(query))
    return ChatOpenAI(model=MODEL).invoke([
        SystemMessage(content="Ответь на вопрос о человеке, опираясь ТОЛЬКО на профили ниже."),
        HumanMessage(content=f"Профили:\n{context}\n\nВопрос: {query}"),
    ]).content


if __name__ == "__main__":
    write(PROFILES)
    print(f"\n💬 Ответ:\n{answer('Кто создал язык Python?')}")
