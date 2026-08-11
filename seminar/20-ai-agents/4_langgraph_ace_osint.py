"""
Showcase 4 — LangGraph + ACE: Self-Evolving OSINT Agent
=======================================================
Агент собирает досье на человека и между итерациями переписывает
собственный «плейбук» правил поиска (Agentic Context Engineering).

Граф:  START → generator → rag_upsert → reflector ─(done|limit)→ END
                   ▲                          └→ curator ─┘
"""
import json
import os
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

    for idx in sorted({i for i in remove}, reverse=True):
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


_STORE = None


def get_store() -> Chroma:
    """Ленивая инициализация Chroma. В offline/selftest — детерминированные фейковые эмбеддинги."""
    global _STORE
    if _STORE is None:
        if OFFLINE or "--selftest" in sys.argv:
            from langchain_core.embeddings import DeterministicFakeEmbedding
            embeddings = DeterministicFakeEmbedding(size=64)
        else:
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        _STORE = Chroma(collection_name="profiles",
                        embedding_function=embeddings,
                        persist_directory=CHROMA_DIR)
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


def require_keys() -> None:
    """Падаем сразу, а не через три LLM-вызова."""
    missing = [k for k in ("OPENAI_API_KEY", "EXA_API_KEY") if not os.getenv(k)]
    if missing:
        sys.exit(f"❌ Нет переменных окружения: {', '.join(missing)}. "
                 f"Добавь их в .env в корне репозитория или запусти с --offline.")


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
    messages: Annotated[list, add_messages]   # история вызовов тулов
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

    extracted = ChatOpenAI(model=MODEL).with_structured_output(Facts).invoke(
        convo + [HumanMessage(content="Верни извлечённые факты по слотам досье.")]
    )
    facts = {k: v for k, v in extracted.model_dump().items() if v.strip()}
    print(f"  📦 извлечено слотов: {len(facts)}")
    return {"facts": facts,
            "iterations": state["iterations"] + 1,
            "messages": [AIMessage(content=f"Итерация {state['iterations'] + 1}: "
                                           f"найдено {len(facts)} слотов")]}


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


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    print("CLI появится в задаче 8")
