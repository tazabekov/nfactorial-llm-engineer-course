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


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    print("CLI появится в задаче 8")
