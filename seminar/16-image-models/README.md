# 16 — AI-Оценка и Виртуальный Стейджинг Недвижимости

Цель: оценить состояние квартиры по фото с помощью Vision-Language модели (Gemini)
и показать результат в виде отчёта оценщика, а также переоформить интерьер (виртуальный
стейджинг) на локальном сайте.

**Стек:** Python 3.12, FastAPI, `google-genai` (Gemini API), PostgreSQL (Neon), ванильный HTML/CSS/JS.

---

## Установка

```bash
# 1. Создать и активировать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить ключ API и базу данных
cp .env.example .env
# впишите в .env свой GEMINI_API_KEY (см. https://aistudio.google.com/apikey)
# и DATABASE_URL для PostgreSQL (см. раздел "Задание 3" ниже)

# 4. Создать таблицу furniture_catalog и заполнить её данными
psql "$DATABASE_URL" -f schema.sql
```

---

## Запуск

```bash
source .venv/bin/activate
uvicorn app:app --reload
```

Откройте [http://127.0.0.1:8000](http://127.0.0.1:8000) в браузере.

---

## Файлы проекта

| Файл | Назначение |
|---|---|
| `scoring.py` | Системный промпт, Pydantic-схема оценки, вызов Gemini VL модели (Задание 1) |
| `staging.py` | Виртуальный стейджинг: редактирование фото через Gemini image-модель (Задание 2) |
| `furniture.py` | Извлечение атрибутов мебели + SQL-сопоставление с `furniture_catalog` (Задание 3) |
| `schema.sql` | DDL + моковые данные для таблицы `furniture_catalog` |
| `app.py` | FastAPI-сервер: отдаёт страницу, `POST /analyze`, `POST /stage`, `POST /report` |
| `static/` | Фронтенд (фото → отчёт оценщика → стейджинг → итоговый отчёт со стоимостью) |
| `requirements.txt` | Python-зависимости |

---

## Задание 1 — AI-Scoring (Оценка квартиры по фото)

Загрузите фотографию комнаты/квартиры и нажмите **«Оценить квартиру»**. Модель
играет роль опытного оценщика недвижимости и возвращает строгий JSON с оценками
от 1 до 10 по пяти критериям:

- 🧹 **Чистота и порядок** (Cleanliness)
- 🔨 **Состояние ремонта** (Repair Condition)
- 🛋 **Актуальность дизайна** (Modernity)
- ☀️ **Освещенность** (Lighting)
- 📦 **Захламленность** (Clutter)

...плюс краткий вердикт оценщика (`summary`).

Структурированный вывод обеспечивается через `response_mime_type="application/json"`
+ `response_schema=ApartmentScore` (Pydantic-модель) в `scoring.py` — Gemini
гарантированно возвращает JSON, соответствующий схеме.

**Критерий приёмки:** после загрузки фото и нажатия «Оценить квартиру» на странице
появляются все 5 баллов (1–10), общий средний балл и вердикт оценщика.

---

## Задание 2 — Виртуальный стейджинг (шаг 03 в UI)

Используя то же загруженное в шаге 01 фото, опишите текстом, что нужно
изменить (заменить/добавить/убрать мебель), настройте гиперпараметры и нажмите
**«Преобразить квартиру»** — страница покажет фото «до/после» рядом.

Гиперпараметры (с значениями по умолчанию, `staging.py`):

| Параметр | По умолчанию | Диапазон |
|---|---|---|
| `temperature` | 1.0 | 0.0–2.0 |
| `top_p` | 0.95 | 0.0–1.0 |
| `top_k` | 40 | 1–64 |
| `seed` | случайный (не задан) | любое целое, для воспроизводимости |

> **Важно про гиперпараметры.** В условии задания приведён пример с
> `guidance_scale`, `number_of_inference_steps` и `image_strength` — это
> параметры Stable Diffusion-подобных API. Реальный Gemini image API
> (`gemini-2.5-flash-image`, она же Nano Banana) через `google-genai` таких
> параметров не принимает; он поддерживает `temperature`, `top_p`, `top_k` и
> `seed` в `GenerateContentConfig`, поэтому именно они вынесены в UI как
> честный, работающий эквивалент.

**Как задокументировать эксперимент "было/стало":** загрузите одно и то же фото,
меняйте по одному параметру за раз (зафиксировав `seed`, чтобы сравнение было
честным), и сохраняйте пары изображений «до/после» из блока сравнения на
странице — это и есть результат для отчёта по гиперпараметрам.

**Критерий приёмки:** после ввода промпта и нажатия «Преобразить квартиру» на
странице появляется отредактированное фото (оригинал уже виден в шаге 01, поэтому
повторно не дублируется).

---

## Задание 3 — Интеграция с базой данных PostgreSQL (шаг 04 в UI)

**База данных:** PostgreSQL, поднята как Neon (через Vercel Marketplace):

```bash
vercel integration add neon      # провижининг + автоматическая инъекция DATABASE_URL
                                  # в переменные окружения проекта (все окружения)
psql "$DATABASE_URL" -f schema.sql
```

Для локального запуска скопируйте `DATABASE_URL` из `.env.local` (создаётся
командой выше) в свой `.env`. На Vercel переменная уже прописана автоматически
для production/preview/development.

`schema.sql` создаёт таблицу `furniture_catalog` (id, category, subcategory,
brand, model_name, style, color, material, price_kzt, in_stock, rating,
description) и заполняет её 16 позициями мебели с реальными на вид ценами в тенге.

**Логика связки (`furniture.py`):**

1. `extract_furniture_attributes()` — Gemini VL смотрит на фото «после» из
   шага 03 и извлекает строгий JSON: `category`, `style`, `color`,
   `display_name` (те же значения категорий/стилей, что и в каталоге).
2. `find_matching_furniture()` — обычный SQL-запрос: `WHERE category = ...`,
   затем ранжирование оставшихся строк по совпадению `style`/`color`
   (`ORDER BY style_match DESC, color_match DESC, rating DESC LIMIT 1`).
3. `POST /report` в `app.py` дополнительно повторно оценивает фото «после»
   через `score_apartment_photo()` (Задание 1), чтобы получить актуальный
   балл `modernity`, и собирает итоговый текст:

   > «Квартира преобразилась! Оценка дизайна выросла с 4 до 8. Добавленная
   > мебель: Светло-серый диван (Modern). Примерная стоимость обновления:
   > 350 000 тг.»

Кнопка «Рассчитать стоимость обновления» (шаг 04) становится активной, как
только пройдены шаг 02 (есть оценка «до») и шаг 03 (есть фото «после»).

**Критерий приёмки:** после нажатия кнопки на странице появляется текстовый
отчёт и карточка с найденной позицией каталога, её стилем/цветом и ценой.

---

## Отладка без браузера

```bash
source .venv/bin/activate
python - <<'EOF'
from scoring import score_apartment_photo
from staging import stage_photo
from furniture import extract_furniture_attributes, find_matching_furniture

with open("путь/к/фото.jpg", "rb") as f:
    image_bytes = f.read()

before = score_apartment_photo(image_bytes, "image/jpeg")
print(before)

prompt = "Replace the old sofa with a modern yellow scandinavian sofa"
result_bytes, result_mime = stage_photo(
    image_bytes, "image/jpeg", prompt,
    temperature=1.0, top_p=0.95, top_k=40,
)
with open("staged_room.png", "wb") as f:
    f.write(result_bytes)

attrs = extract_furniture_attributes(result_bytes, result_mime, prompt)
print(attrs)
print(find_matching_furniture(attrs))
EOF
```
