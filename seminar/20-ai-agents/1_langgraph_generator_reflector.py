"""
Showcase 1 — LangGraph: Generator + Tool + Reflector
=====================================================
Пользователь просит стих → Generator вызывает инструмент write_poem →
Reflector оценивает результат → если слабо, отправляет на переделку.

Граф:  START → generator → tools → reflector ─(good)→ END
                    ▲                        └(retry)→ generator
"""
import os
import json
from typing import Annotated, Literal
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END

load_dotenv()
MODEL = os.getenv("GENERATOR_MODEL", "gpt-5.6-terra")


@tool
def write_poem(topic: str, style: str = "free verse") -> str:
    """Пишет короткий стих на заданную тему в заданном стиле."""
    llm = ChatOpenAI(model=MODEL)
    return llm.invoke(f"Напиши короткий стих ({style}) на тему: {topic}").content


llm_with_tool = ChatOpenAI(model=MODEL, reasoning_effort="none").bind_tools([write_poem])


def generator(state: MessagesState) -> dict:
    return {"messages": [llm_with_tool.invoke(state["messages"])]}


def tools(state: MessagesState) -> dict:
    call = state["messages"][-1].tool_calls[0]
    result = write_poem.invoke(call["args"])
    print(f"\n📜 Стих:\n{result}\n")
    return {"messages": [ToolMessage(content=result, tool_call_id=call["id"])]}


def reflector(state: MessagesState) -> dict:
    poem = state["messages"][-1].content
    verdict = ChatOpenAI(model=MODEL).invoke([
        SystemMessage(content='Оцени стих. Верни JSON {"good": true|false, "note": "..."}'),
        HumanMessage(content=poem),
    ]).content
    data = json.loads(verdict[verdict.find("{"): verdict.rfind("}") + 1])
    print(f"🧐 Reflector: good={data['good']} — {data['note']}")
    return {"messages": [AIMessage(content=f"[{'GOOD' if data['good'] else 'RETRY'}] {data['note']}")]}


def route_after_generator(state: MessagesState) -> Literal["tools", "reflector"]:
    return "tools" if state["messages"][-1].tool_calls else "reflector"


def route_after_reflector(state: MessagesState) -> Literal["generator", "__end__"]:
    return END if state["messages"][-1].content.startswith("[GOOD]") else "generator"


def build():
    g = StateGraph(MessagesState)
    g.add_node("generator", generator)
    g.add_node("tools", tools)
    g.add_node("reflector", reflector)
    g.add_edge(START, "generator")
    g.add_conditional_edges("generator", route_after_generator, ["tools", "reflector"])
    g.add_edge("tools", "reflector")
    g.add_conditional_edges("reflector", route_after_reflector, ["generator", END])
    return g.compile()


if __name__ == "__main__":
    topic = input("О чём написать стих? ").strip() or "осень в Алматы"
    build().invoke({"messages": [HumanMessage(content=f"Напиши стих про {topic}")]})
