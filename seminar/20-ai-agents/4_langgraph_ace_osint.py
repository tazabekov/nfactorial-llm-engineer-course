"""
Showcase 4 — LangGraph + ACE: Self-Evolving OSINT Agent
=======================================================
Агент собирает досье на человека и между итерациями переписывает
собственный «плейбук» правил поиска (Agentic Context Engineering).

Граф:  START → generator → rag_upsert → reflector ─┬─(done | лимит)→ END
                   ▲                               │
                   └─────────── curator ←──────────┘
"""
import json
import os
import shutil
import sys
from typing import Annotated, Dict, List, Literal, TypedDict

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

load_dotenv()
MODEL = os.getenv("GENERATOR_MODEL", "gpt-5.6-terra")

SLOTS = ["role_title", "organization", "education",
         "notable_work", "online_presence", "location"]
SLOT_RU = {
    "role_title": "кем работает / должность",
    "organization": "компания или проект",
    "education": "образование",
    "notable_work": "заметные проекты, публикации, репозитории",
    "online_presence": "соцсети, личный сайт, профили",
    "location": "город или страна",
}

MAX_ITER = 3
MAX_TOOL_CALLS = 6
PLAYBOOK_LIMIT = 7
SLOT_CHAR_CAP = 500

CHROMA_DIR = "./chroma_osint"
PLAYBOOK_PATH = "./playbook.json"

BASE_PLAYBOOK = [
    "Всегда добавляй к ФИО контекст специальности и города из запроса пользователя.",
    "Проверяй, что найденная страница про нужного человека, а не однофамильца — сверяй специальность.",
]

OFFLINE = False


def merge_slot(old: str, new: str) -> str:
    """Детерминированный мерж значения слота: без LLM, без потери старого."""
    old, new = (old or "").strip(), (new or "").strip()
    if not new:
        return old
    if not old:
        return new[:SLOT_CHAR_CAP]
    if new.lower() in old.lower():
        return old
    return f"{old}; {new}"[:SLOT_CHAR_CAP]


def apply_playbook_ops(playbook: list[str], add: list[str],
                       remove: list[int]) -> tuple[list[str], list[str], list[str], list[str]]:
    """Инкрементально правит плейбук.

    Возвращает (новый плейбук, добавленные, удалённые Curator'ом, вытесненные лимитом).
    Последние два списка разделены намеренно: вытеснение по лимиту — не решение
    Curator'а, и приписывать их ему в выводе значило бы врать про эволюцию правил.

    remove — 1-based индексы, как в пронумерованном списке, который видел Curator.
    Базовые правила закреплены: их нельзя удалить и они не вытесняются лимитом.
    """
    pinned = set(BASE_PLAYBOOK)
    result, removed, evicted = list(playbook), [], []

    for idx in sorted(set(remove), reverse=True):
        pos = idx - 1
        if not (0 <= pos < len(result)):
            continue
        if result[pos] in pinned:
            continue
        removed.append(result.pop(pos))

    added = []
    for rule in add:
        rule = (rule or "").strip()
        if rule and rule not in result:
            result.append(rule)
            added.append(rule)

    while len(result) > PLAYBOOK_LIMIT:
        victim = next((r for r in result if r not in pinned), None)
        if victim is None:
            break
        result.remove(victim)
        evicted.append(victim)

    return result, added, removed, evicted


def decide_missing(dossier: Dict[str, str], reported: List[str]) -> List[str]:
    """Слот незакрыт, если он пуст в досье ИЛИ Рефлектор усомнился в нём.

    Рефлектор может только добавить сомнение, но не объявить готовность:
    пустой слот остаётся в missing, что бы модель ни ответила.
    """
    empty = {s for s in SLOTS if not (dossier.get(s) or "").strip()}
    doubted = {s for s in reported if s in SLOTS}
    return sorted(empty | doubted, key=SLOTS.index)


_STORE = None


def get_store() -> Chroma:
    """Ленивая инициализация Chroma. В offline/selftest — детерминированные фейковые эмбеддинги."""
    global _STORE
    if _STORE is None:
        if OFFLINE:
            from langchain_core.embeddings import DeterministicFakeEmbedding
            embeddings = DeterministicFakeEmbedding(size=64)
        else:
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Фейковые эмбеддинги 64-мерные, настоящие — 1536. Коллекция Chroma имеет
        # фиксированную размерность, поэтому офлайн-данные держим отдельно, иначе
        # следующий запуск в другом режиме падает на add_texts.
        _STORE = Chroma(collection_name="profiles",
                        embedding_function=embeddings,
                        persist_directory=f"{CHROMA_DIR}_offline" if OFFLINE else CHROMA_DIR)
    return _STORE


@tool
def query_profile(name: str) -> dict:
    """Возвращает уже собранное досье на человека: {слот: значение}."""
    got = get_store().get(where={"name": name})
    dossier = {}
    for doc, meta in zip(got["documents"], got["metadatas"]):
        dossier[meta["slot"]] = doc
    return dossier


@tool
def upsert_profile(name: str, facts: dict) -> dict:
    """Создаёт или мержит факты в досье. Возвращает досье целиком после записи."""
    current = query_profile.invoke({"name": name})
    merged = {}
    for slot, value in (facts or {}).items():
        if slot not in SLOTS:
            continue
        new_value = merge_slot(current.get(slot, ""), str(value or ""))
        if new_value:
            merged[slot] = new_value
    if merged:
        get_store().add_texts(
            texts=list(merged.values()),
            metadatas=[{"name": name, "slot": s} for s in merged],
            ids=[f"{name}::{s}" for s in merged],
        )
    return {**current, **merged}


OFFLINE_FIXTURES = {
    "search": [
        {"title": "Арман Сулейменов — nFactorial School",
         "url": "https://example.org/armanulean",
         "text": "Основатель школы программирования nFactorial в Алматы."},
        {"title": "Однофамилец: Арман Сулейменов, строитель",
         "url": "https://example.org/wrong-person",
         "text": "Прораб строительной компании в Астане. Не имеет отношения к IT."},
    ],
    "pages": {
        "https://example.org/armanulean": (
            "# Арман Сулейменов\n\n"
            "Основатель школы программирования nFactorial (Алматы, Казахстан). "
            "Выпускник Purdue University, финалист ACM ICPC. "
            "Основал Zero To One Labs. GitHub: github.com/example.\n"
        ),
        "https://example.org/wrong-person": (
            "# Арман Сулейменов\n\nПрораб строительной компании в Астане.\n"
        ),
    },
}


def require_keys(offline: bool) -> None:
    """Падаем сразу, а не через три LLM-вызова.

    --offline подменяет только веб-инструменты; узлы графа всё равно зовут OpenAI.
    """
    needed = ["OPENAI_API_KEY"] if offline else ["OPENAI_API_KEY", "EXA_API_KEY"]
    missing = [k for k in needed if not os.getenv(k)]
    if missing:
        sys.exit(f"❌ Нет переменных окружения: {', '.join(missing)}. "
                 f"Добавь их в .env в корне репозитория.")


@tool
def exa_search(query: str, num_results: int = 5) -> str:
    """Семантический веб-поиск через Exa AI. Возвращает JSON со списком title/url/text."""
    if OFFLINE:
        return json.dumps(OFFLINE_FIXTURES["search"][:num_results], ensure_ascii=False)
    try:
        r = requests.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": os.getenv("EXA_API_KEY", "")},
            json={"query": query, "numResults": num_results,
                  "contents": {"text": {"maxCharacters": 400}}},
            timeout=20,
        )
        if r.status_code != 200:
            return json.dumps({"error": f"Exa вернул {r.status_code}: {r.text[:200]}"},
                              ensure_ascii=False)
        results = [{"title": x.get("title"), "url": x.get("url"),
                    "text": (x.get("text") or "")[:400]}
                   for x in r.json().get("results", [])]
        return json.dumps(results, ensure_ascii=False)
    except requests.RequestException as e:
        return json.dumps({"error": f"Exa недоступен: {e}"}, ensure_ascii=False)


@tool
def jina_reader(url: str) -> str:
    """Скрапит страницу через Jina Reader и возвращает чистый Markdown."""
    if OFFLINE:
        return OFFLINE_FIXTURES["pages"].get(url, f"OFFLINE: нет фикстуры для {url}")
    headers = {"Accept": "text/markdown"}
    if os.getenv("JINA_API_KEY"):
        headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
    try:
        r = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=25)
        if r.status_code != 200:
            return f"[ошибка скрапинга] Jina вернул {r.status_code} для {url}"
        return r.text[:4000]
    except requests.RequestException as e:
        return f"[ошибка скрапинга] {url} недоступен: {e}"


class AgentState(TypedDict):
    target_person: str                        # кого ищем (ФИО + контекст)
    playbook: List[str]                       # ключевая фишка ACE: правила поиска
    insights: str                             # выводы Reflector
    messages: Annotated[list, add_messages]   # по одной сводке на итерацию (сам
                                              # tool-трейс остаётся локальным в generator)
    iterations: int                           # счётчик циклов
    facts: Dict[str, str]                     # выход Generator → вход RAG_Upsert
    missing: List[str]                        # незакрытые слоты → вход Curator
    done: bool                                # решение для условного ребра


class Facts(BaseModel):
    """Факты, извлечённые за одну итерацию. Пустая строка = не нашли."""
    role_title: str = Field("", description="должность или род занятий")
    organization: str = Field("", description="компания, школа или проект")
    education: str = Field("", description="университет, степень")
    notable_work: str = Field("", description="проекты, публикации, репозитории")
    online_presence: str = Field("", description="соцсети, личный сайт, профили")
    location: str = Field("", description="город или страна")


class Reflection(BaseModel):
    missing: List[str] = Field(default_factory=list,
                               description="слоты досье, которые всё ещё пусты или сомнительны")
    insights: str = Field("", description="конкретный урок: что пошло не так в поиске")


class PlaybookOps(BaseModel):
    add: List[str] = Field(default_factory=list, description="новые правила поиска")
    remove: List[int] = Field(default_factory=list,
                              description="номера правил для удаления, нумерация с 1")


TOOLS = {"exa_search": exa_search, "jina_reader": jina_reader}


def format_playbook(playbook: List[str]) -> str:
    if not playbook:
        return "(пусто)"
    return "\n".join(f"{i}. {rule}" for i, rule in enumerate(playbook, 1))


def format_dossier(dossier: Dict[str, str]) -> str:
    lines = [f"  - {SLOT_RU[s]}: {dossier.get(s) or '—'}" for s in SLOTS]
    return "\n".join(lines)


GENERATOR_SYSTEM = """Ты OSINT-исследователь. Твоя задача — собрать досье на человека.

ПЛЕЙБУК (правила, выученные на прошлых итерациях, соблюдай их):
{playbook}

УЖЕ ИЗВЕСТНО:
{dossier}

НУЖНО НАЙТИ В ЭТОЙ ИТЕРАЦИИ: {missing}

Используй exa_search, чтобы найти страницы, и jina_reader, чтобы прочитать самые
перспективные из них. Сначала ищи, потом читай — не выдумывай URL.
Не более {max_calls} вызовов инструментов. Затем верни найденные факты.
Если факт не подтверждён прочитанной страницей — оставь поле пустым."""


def generator(state: AgentState) -> dict:
    dossier = query_profile.invoke({"name": state["target_person"]})
    missing = state.get("missing") or SLOTS
    system = GENERATOR_SYSTEM.format(
        playbook=format_playbook(state["playbook"]),
        dossier=format_dossier(dossier),
        missing=", ".join(SLOT_RU[s] for s in missing),
        max_calls=MAX_TOOL_CALLS,
    )
    llm = ChatOpenAI(model=MODEL, reasoning_effort="none").bind_tools(list(TOOLS.values()))
    convo = [SystemMessage(content=system),
             HumanMessage(content=f"Цель: {state['target_person']}")]

    # Бюджет проверяется на границе хода, а не перед каждым вызовом: если модель
    # вернула пачку tool_calls, мы обязаны ответить ToolMessage на КАЖДЫЙ из них,
    # иначе следующий запрос к API упадёт. Перерасход ограничен размером пачки.
    calls_made = 0
    while calls_made < MAX_TOOL_CALLS:
        ai = llm.invoke(convo)
        convo.append(ai)
        if not ai.tool_calls:
            break
        for call in ai.tool_calls:
            print(f"  🛠  {call['name']}({json.dumps(call['args'], ensure_ascii=False)[:120]})")
            convo.append(ToolMessage(content=TOOLS[call["name"]].invoke(call["args"]),
                                     tool_call_id=call["id"]))
            calls_made += 1

    # У цикла tool-calling reasoning_effort="none": он механический. Извлечению
    # фактов рассуждение полезно, поэтому здесь параметр не задаём.
    extracted = ChatOpenAI(model=MODEL).with_structured_output(Facts).invoke(
        convo + [HumanMessage(content="Верни извлечённые факты по слотам досье.")]
    )
    facts = {k: v for k, v in extracted.model_dump().items() if v.strip()}
    print(f"  📦 извлечено слотов: {len(facts)}")
    return {"facts": facts,
            "iterations": state["iterations"] + 1,
            "messages": [AIMessage(content=f"Итерация {state['iterations'] + 1}: "
                                           f"найдено {len(facts)} слотов")]}


def rag_upsert(state: AgentState) -> dict:
    """Детерминированный узел: мержит факты в векторную БД, LLM не участвует."""
    facts = state.get("facts") or {}
    if not facts:
        print("  💾 нечего сохранять")
        return {}
    dossier = upsert_profile.invoke({"name": state["target_person"], "facts": facts})
    print(f"  💾 записано слотов: {len(facts)} → всего в досье: {len(dossier)}")
    return {}


REFLECTOR_SYSTEM = """Ты критик OSINT-исследования. Оцени собранное досье.

Верни:
- missing: список слотов, которые пусты ИЛИ вызывают сомнение (похоже на однофамильца,
  факт не подтверждён источником). Допустимые значения: {slots}
- insights: один конкретный урок для следующей попытки поиска. Не общие слова, а
  что именно пошло не так. Например: «Искали без указания специальности, и Jina принёс
  статью про строителя вместо AI-инженера»."""


def reflector(state: AgentState) -> dict:
    dossier = query_profile.invoke({"name": state["target_person"]})
    review = ChatOpenAI(model=MODEL).with_structured_output(Reflection).invoke([
        SystemMessage(content=REFLECTOR_SYSTEM.format(slots=", ".join(SLOTS))),
        HumanMessage(content=f"Цель: {state['target_person']}\n\n"
                             f"Досье:\n{format_dossier(dossier)}"),
    ])
    missing = decide_missing(dossier, review.missing)
    done = not missing
    status = "досье полное" if done else f"не хватает: {', '.join(missing)}"
    print(f"  🧐 Reflector: {status}\n     insight: {review.insights}")
    return {"insights": review.insights, "missing": missing, "done": done}


CURATOR_SYSTEM = """Ты куратор контекста агента. У агента есть плейбук — список правил поиска.

ТЕКУЩИЙ ПЛЕЙБУК:
{playbook}

Внеси ТОЧЕЧНЫЕ правки, опираясь на урок Рефлектора:
- add: 1-2 новых конкретных правила. Правило должно менять поведение поиска
  (что добавить в запрос, где искать, что перепроверить), а не описывать цель.
- remove: номера правил, которые доказали свою бесполезность. Нумерация с 1.
  Правила 1–{base_count} базовые, их удалять нельзя.

Не переписывай плейбук целиком."""


def curator(state: AgentState) -> dict:
    ops = ChatOpenAI(model=MODEL).with_structured_output(PlaybookOps).invoke([
        SystemMessage(content=CURATOR_SYSTEM.format(
            playbook=format_playbook(state["playbook"]),
            base_count=len(BASE_PLAYBOOK))),
        HumanMessage(content=f"Урок Рефлектора: {state['insights']}\n"
                             f"Не хватает слотов: {', '.join(state['missing'])}"),
    ])
    playbook, added, removed, evicted = apply_playbook_ops(
        state["playbook"], ops.add, ops.remove)
    for rule in removed:
        print(f"  ✍  - {rule}")
    for rule in added:
        print(f"  ✍  + {rule}")
    for rule in evicted:
        print(f"  ⤵  вытеснено лимитом: {rule}")
    print(f"\n  📋 ПЛЕЙБУК после итерации {state['iterations']}:\n"
          f"{format_playbook(playbook)}\n")
    return {"playbook": playbook}


def make_router(max_iter: int):
    """Единственное условное ребро графа — после Reflector."""
    def route_after_reflector(state: AgentState) -> Literal["curator", "__end__"]:
        if state["done"] or state["iterations"] >= max_iter:
            return END
        return "curator"
    return route_after_reflector


def build(max_iter: int = MAX_ITER):
    g = StateGraph(AgentState)
    g.add_node("generator", generator)
    g.add_node("rag_upsert", rag_upsert)
    g.add_node("reflector", reflector)
    g.add_node("curator", curator)
    g.add_edge(START, "generator")
    g.add_edge("generator", "rag_upsert")
    g.add_edge("rag_upsert", "reflector")
    g.add_conditional_edges("reflector", make_router(max_iter), ["curator", END])
    g.add_edge("curator", "generator")
    return g.compile()


def load_playbook() -> List[str]:
    """Читает плейбук с диска. Битый файл — не повод падать: скрипт перезаписывает
    его в конце каждого прогона, и оборванная запись иначе заблокировала бы запуск."""
    try:
        with open(PLAYBOOK_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        if not isinstance(saved, list):
            raise ValueError("playbook.json должен содержать список правил")
    except FileNotFoundError:
        return list(BASE_PLAYBOOK)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"⚠️  {PLAYBOOK_PATH} повреждён ({e}), стартую с базового плейбука")
        return list(BASE_PLAYBOOK)
    # базовые правила закреплены — восстанавливаем, если файл их потерял
    return list(BASE_PLAYBOOK) + [r for r in saved if r not in BASE_PLAYBOOK]


def save_playbook(playbook: List[str]) -> None:
    with open(PLAYBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(playbook, f, ensure_ascii=False, indent=2)


def reset_local_state() -> None:
    shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    shutil.rmtree(f"{CHROMA_DIR}_offline", ignore_errors=True)
    if os.path.exists(PLAYBOOK_PATH):
        os.remove(PLAYBOOK_PATH)
    print("🧹 Сброшено: chroma_osint/, chroma_osint_offline/ и playbook.json")


def main() -> None:
    global OFFLINE
    OFFLINE = "--offline" in sys.argv
    if "--reset" in sys.argv:
        reset_local_state()
    max_iter = MAX_ITER
    if "--max-iter" in sys.argv:
        try:
            max_iter = int(sys.argv[sys.argv.index("--max-iter") + 1])
        except (IndexError, ValueError):
            sys.exit("❌ --max-iter требует целое число, например: --max-iter 2")
        if max_iter < 1:
            sys.exit("❌ --max-iter должен быть не меньше 1")
    require_keys(OFFLINE)

    target = input("Кого ищем? (ФИО + специальность + город, "
                   "например «Арман Сулейменов, основатель школы nFactorial, Алматы»)\n> ").strip()
    if not target:
        sys.exit("Пустая цель — нечего искать.")

    playbook = load_playbook()
    print(f"\n📋 СТАРТОВЫЙ ПЛЕЙБУК:\n{format_playbook(playbook)}\n")

    final = build(max_iter).invoke(
        {"target_person": target, "playbook": playbook, "insights": "",
         "messages": [], "iterations": 0, "facts": {}, "missing": [], "done": False},
        {"recursion_limit": 25},
    )
    save_playbook(final["playbook"])

    dossier = query_profile.invoke({"name": target})
    print(f"\n{'=' * 60}\n📇 ИТОГОВОЕ ДОСЬЕ: {target}\n{'=' * 60}")
    print(format_dossier(dossier))
    print(f"\nИтераций: {final['iterations']} | "
          f"Не закрыто слотов: {len(final['missing'])}")
    print(f"\n📋 ФИНАЛЬНЫЙ ПЛЕЙБУК:\n{format_playbook(final['playbook'])}")


SELFTESTS = []


def selftest(fn):
    """Регистрирует проверку, запускаемую флагом --selftest."""
    SELFTESTS.append(fn)
    return fn


def run_selftest() -> int:
    failures = 0
    for fn in SELFTESTS:
        try:
            fn()
            print(f"  ✅ {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"  ❌ {fn.__name__}: {e}")
        except Exception as e:
            failures += 1
            print(f"  💥 {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(SELFTESTS) - failures}/{len(SELFTESTS)} проверок прошло")
    return 1 if failures else 0


@selftest
def test_config_constants():
    assert SLOTS == ["role_title", "organization", "education",
                     "notable_work", "online_presence", "location"]
    assert set(SLOT_RU) == set(SLOTS)
    assert (MAX_ITER, MAX_TOOL_CALLS, PLAYBOOK_LIMIT, SLOT_CHAR_CAP) == (3, 6, 7, 500)
    assert len(BASE_PLAYBOOK) == 2


@selftest
def test_merge_slot():
    # пустой слот — просто записываем
    assert merge_slot("", "CEO") == "CEO"
    # пустое новое значение ничего не портит
    assert merge_slot("CEO", "") == "CEO"
    # повтор не дублируется
    assert merge_slot("CEO", "CEO") == "CEO"
    # подстрока не дублируется
    assert merge_slot("CEO компании nFactorial", "CEO") == "CEO компании nFactorial"
    # подстрока сравнивается без учёта регистра
    assert merge_slot("CEO компании", "ceo") == "CEO компании"
    # новое значение дописывается
    assert merge_slot("CEO", "основатель") == "CEO; основатель"
    # пробелы обрезаются
    assert merge_slot("  CEO  ", "  основатель  ") == "CEO; основатель"
    # потолок соблюдается
    long_old = "x" * (SLOT_CHAR_CAP - 2)
    assert len(merge_slot(long_old, "новый факт")) <= SLOT_CHAR_CAP


@selftest
def test_apply_playbook_ops():
    base = list(BASE_PLAYBOOK)

    # добавление в конец
    pb, added, removed, evicted = apply_playbook_ops(base, ["правило A"], [])
    assert pb == base + ["правило A"]
    assert added == ["правило A"] and removed == [] and evicted == []

    # remove 1-based: удаляем третье правило, базовые не трогаем
    pb2, _, removed2, evicted2 = apply_playbook_ops(pb, [], [3])
    assert pb2 == base and removed2 == ["правило A"] and evicted2 == []

    # закреплённые базовые правила нельзя удалить
    pb3, _, removed3, _ = apply_playbook_ops(base, [], [1, 2])
    assert pb3 == base and removed3 == []

    # индексы вне диапазона игнорируются
    pb4, _, _, _ = apply_playbook_ops(base, [], [0, 99, -1])
    assert pb4 == base

    # дубли не добавляются
    pb5, added5, _, _ = apply_playbook_ops(base, [base[0]], [])
    assert pb5 == base and added5 == []

    # лимит вытесняет самое старое НЕзакреплённое правило
    many = base + [f"правило {i}" for i in range(5)]
    assert len(many) == PLAYBOOK_LIMIT
    pb6, _, removed6, evicted6 = apply_playbook_ops(many, ["правило new"], [])
    assert len(pb6) == PLAYBOOK_LIMIT
    assert pb6[:2] == base                 # базовые уцелели
    assert "правило 0" not in pb6          # вытеснено самое старое
    assert "правило new" in pb6
    # вытеснение по лимиту не приписывается Curator'у
    assert removed6 == [] and evicted6 == ["правило 0"]

    # удаление и вытеснение в одном вызове не смешиваются
    pb7, added7, removed7, evicted7 = apply_playbook_ops(
        many, ["правило X", "правило Y"], [3])
    assert removed7 == ["правило 0"]       # запросил Curator (индекс 3)
    assert evicted7 == ["правило 1"]       # выдавил лимит
    assert added7 == ["правило X", "правило Y"]
    assert len(pb7) == PLAYBOOK_LIMIT


@selftest
def test_decide_missing():
    full = {s: "значение" for s in SLOTS}
    # модель молчит, досье полное → готово
    assert decide_missing(full, []) == []
    # модель не может объявить готовность при пустых слотах
    assert decide_missing({}, []) == SLOTS
    # пробелы не считаются заполненным слотом
    assert decide_missing({**full, "education": "   "}, []) == ["education"]
    # сомнение модели добавляется к пустым слотам
    assert decide_missing(full, ["location"]) == ["location"]
    # мусорные имена слотов от модели отбрасываются
    assert decide_missing(full, ["хобби", "role_title"]) == ["role_title"]
    # порядок совпадает с порядком SLOTS
    assert decide_missing({}, []) == sorted(SLOTS, key=SLOTS.index)


@selftest
def test_profile_roundtrip():
    import tempfile
    global CHROMA_DIR, _STORE
    prev_dir, prev_store = CHROMA_DIR, _STORE
    try:
        CHROMA_DIR = tempfile.mkdtemp(prefix="chroma_selftest_")
        _STORE = None

        # пустая база — пустое досье
        assert query_profile.invoke({"name": "Тест Тестов"}) == {}

        upsert_profile.invoke({"name": "Тест Тестов",
                               "facts": {"role_title": "CEO", "location": "Алматы"}})
        got = query_profile.invoke({"name": "Тест Тестов"})
        assert got["role_title"] == "CEO"
        assert got["location"] == "Алматы"
        assert "education" not in got

        # повторный upsert мержит, а не дублирует
        upsert_profile.invoke({"name": "Тест Тестов",
                               "facts": {"role_title": "основатель"}})
        got2 = query_profile.invoke({"name": "Тест Тестов"})
        assert got2["role_title"] == "CEO; основатель"

        # чужое имя не протекает
        assert query_profile.invoke({"name": "Другой Человек"}) == {}

        # неизвестные слоты отбрасываются
        upsert_profile.invoke({"name": "Тест Тестов", "facts": {"хобби": "шахматы"}})
        assert "хобби" not in query_profile.invoke({"name": "Тест Тестов"})
    finally:
        CHROMA_DIR, _STORE = prev_dir, prev_store


@selftest
def test_tools_offline():
    import json as _json
    global OFFLINE
    prev = OFFLINE
    try:
        OFFLINE = True
        results = _json.loads(exa_search.invoke({"query": "кто угодно"}))
        assert isinstance(results, list) and results, "офлайн-фикстура должна вернуть результаты"
        assert {"title", "url", "text"} <= set(results[0])

        page = jina_reader.invoke({"url": results[0]["url"]})
        assert isinstance(page, str) and len(page) > 50

        # неизвестный URL не падает, а сообщает об этом
        miss = jina_reader.invoke({"url": "https://example.com/нет-такого"})
        assert "OFFLINE" in miss
    finally:
        OFFLINE = prev


@selftest
def test_exa_error_is_visible():
    """Ошибка Exa должна дойти до LLM текстом, а не превратиться в пустой список.

    Сеть не трогаем: подменяем requests.post, чтобы проверить обе ветки отказа.
    """
    import json as _json
    global OFFLINE

    class _Unauthorized:
        status_code = 401
        text = "unauthorized"

    prev_offline, real_post = OFFLINE, requests.post
    try:
        OFFLINE = False

        requests.post = lambda *a, **kw: _Unauthorized()
        payload = _json.loads(exa_search.invoke({"query": "проверка кода ответа"}))
        assert isinstance(payload, dict), "ошибка обязана быть объектом, а не списком"
        assert "401" in payload["error"]

        def _boom(*a, **kw):
            raise requests.RequestException("сеть недоступна")

        requests.post = _boom
        payload2 = _json.loads(exa_search.invoke({"query": "проверка обрыва сети"}))
        assert isinstance(payload2, dict)
        assert "недоступен" in payload2["error"]
    finally:
        requests.post = real_post
        OFFLINE = prev_offline


@selftest
def test_state_and_models():
    assert set(AgentState.__annotations__) == {
        "target_person", "playbook", "insights", "messages",
        "iterations", "facts", "missing", "done",
    }
    # Facts покрывает ровно слоты досье
    assert set(Facts.model_fields) == set(SLOTS)
    # необязательные поля: модель может вернуть частичный результат
    assert Facts().model_dump() == {s: "" for s in SLOTS}
    assert set(Reflection.model_fields) == {"missing", "insights"}
    assert set(PlaybookOps.model_fields) == {"add", "remove"}


@selftest
def test_format_playbook():
    out = format_playbook(["первое", "второе"])
    assert "1. первое" in out and "2. второе" in out
    assert format_playbook([]).strip() == "(пусто)"


@selftest
def test_rag_upsert_node():
    import tempfile
    global CHROMA_DIR, _STORE
    prev_dir, prev_store = CHROMA_DIR, _STORE
    try:
        CHROMA_DIR = tempfile.mkdtemp(prefix="chroma_node_")
        _STORE = None
        state = {"target_person": "Узел Проверкин",
                 "facts": {"role_title": "инженер", "location": "Алматы"}}
        out = rag_upsert(state)
        assert out == {}, "узел пишет в Chroma, а не в state"
        stored = query_profile.invoke({"name": "Узел Проверкин"})
        assert stored["role_title"] == "инженер"
    finally:
        CHROMA_DIR, _STORE = prev_dir, prev_store


@selftest
def test_router():
    route = make_router(max_iter=3)
    # досье собрано — выходим
    assert route({"done": True, "missing": [], "iterations": 1}) == END
    # есть пробелы и лимит не достигнут — идём к куратору
    assert route({"done": False, "missing": ["education"], "iterations": 1}) == "curator"
    # лимит достигнут — выходим даже с пробелами
    assert route({"done": False, "missing": ["education"], "iterations": 3}) == END
    assert route({"done": False, "missing": ["education"], "iterations": 4}) == END


@selftest
def test_playbook_persistence():
    import tempfile, os as _os
    global PLAYBOOK_PATH
    prev = PLAYBOOK_PATH
    try:
        PLAYBOOK_PATH = _os.path.join(tempfile.mkdtemp(prefix="pb_"), "playbook.json")
        # файла нет — отдаём базовый плейбук
        assert load_playbook() == BASE_PLAYBOOK
        save_playbook(BASE_PLAYBOOK + ["выученное правило"])
        assert load_playbook() == BASE_PLAYBOOK + ["выученное правило"]
    finally:
        PLAYBOOK_PATH = prev


@selftest
def test_playbook_survives_corruption():
    """Скрипт перезаписывает playbook.json каждый прогон — оборванная запись
    не должна блокировать следующий запуск."""
    import tempfile, os as _os
    global PLAYBOOK_PATH
    prev = PLAYBOOK_PATH
    try:
        PLAYBOOK_PATH = _os.path.join(tempfile.mkdtemp(prefix="pb_bad_"), "playbook.json")

        with open(PLAYBOOK_PATH, "w", encoding="utf-8") as f:
            f.write('["правило", "обрыв на сер')      # оборванный JSON
        assert load_playbook() == BASE_PLAYBOOK

        with open(PLAYBOOK_PATH, "w", encoding="utf-8") as f:
            f.write("")                                # пустой файл
        assert load_playbook() == BASE_PLAYBOOK

        with open(PLAYBOOK_PATH, "w", encoding="utf-8") as f:
            f.write('{"rules": []}')                   # валидный JSON, но не список
        assert load_playbook() == BASE_PLAYBOOK
    finally:
        PLAYBOOK_PATH = prev


@selftest
def test_graph_compiles():
    graph = build(max_iter=3)
    assert graph is not None
    nodes = set(graph.get_graph().nodes)
    assert {"generator", "rag_upsert", "reflector", "curator"} <= nodes


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        OFFLINE = True          # selftest никогда не ходит в сеть
        sys.exit(run_selftest())
    main()
