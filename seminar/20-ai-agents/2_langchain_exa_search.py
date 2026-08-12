"""
Showcase 2 — LangChain + Exa search + Jina Reader scraper
=========================================================
LLM с двумя инструментами: сам ищет через Exa, затем скрапит нужную
страницу через Jina Reader и отвечает на основе извлечённого текста.

Поток:  вопрос → exa_search (найти URL) → jina_reader (скрап страницы) → ответ
"""
import os
import json
from dotenv import load_dotenv

import requests
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()
MODEL = os.getenv("GENERATOR_MODEL", "gpt-5.6-terra")


@tool
def exa_search(query: str, num_results: int = 5) -> str:
    """Семантический веб-поиск через Exa AI. Возвращает title/url/snippet."""
    r = requests.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": os.getenv("EXA_API_KEY")},
        json={"query": query, "numResults": num_results,
              "contents": {"text": {"maxCharacters": 400}}},
        timeout=20,
    )
    results = [{"title": x.get("title"), "url": x.get("url"), "text": (x.get("text") or "")[:400]}
               for x in r.json().get("results", [])]
    return json.dumps(results, ensure_ascii=False)


@tool
def jina_reader(url: str) -> str:
    """Скрапит страницу через Jina Reader и возвращает чистый Markdown."""
    headers = {"Accept": "text/markdown"}
    if os.getenv("JINA_API_KEY"):
        headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
    return requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=25).text[:4000]


TOOLS = {"exa_search": exa_search, "jina_reader": jina_reader}
llm = ChatOpenAI(model=MODEL, reasoning_effort="none").bind_tools(list(TOOLS.values()))


def ask(question: str) -> str:
    messages = [HumanMessage(content=question)]
    for _ in range(4):
        ai = llm.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            return ai.content
        for call in ai.tool_calls:
            print(f"🛠  {call['name']}({call['args']})")
            messages.append(ToolMessage(content=TOOLS[call["name"]].invoke(call["args"]), tool_call_id=call["id"]))
    return "Не уложился в лимит итераций"


if __name__ == "__main__":
    answer = ask("Найди официальный сайт школы nFactorial, ОТКРОЙ страницу и перечисли, что на ней написано о программах обучения.")
    print(f"\n💬 Ответ:\n{answer}")
