"""
Showcase 4 — LangGraph + ACE: Self-Evolving OSINT Agent
=======================================================
Агент собирает досье на человека и между итерациями переписывает
собственный «плейбук» правил поиска (Agentic Context Engineering).

Граф:  START → generator → rag_upsert → reflector ─(done|limit)→ END
                   ▲                          └→ curator ─┘
"""
import os
import sys
from dotenv import load_dotenv

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


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    print("CLI появится в задаче 8")
