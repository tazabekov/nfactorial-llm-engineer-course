# 🧬 Seminar: Naive RAG vs Advanced RAG Showdown

Построим две RAG-системы на одном сложном документе, оценим их на **Golden Dataset (30 Q&A)** и разберём, где наивный подход ломается, а продвинутый — вытягивает качество.

**Deadline:** 20:10

---

## 🎯 Цели задания

- Научиться **строить и дебажить RAG-пайплайны** на реальном сложном документе.
- Сравнить **Naive RAG** и **Advanced RAG** по метрикам поиска и генерации.
- Понять, **какие техники реально дают прирост**, особенно на таблицах и сложной вёрстке.

Результат семинара — ноутбук(и) с:
- реализованными двумя пайплайнами,
- рассчитанными метриками на Golden Dataset,
- коротким разбором «почему Advanced RAG лучше именно здесь».

---

## 📦 Данные и файлы

- **Документ:** годовой отчёт (PDF) по компании (таблицы, графики, сложная вёрстка) — `ilovepdf_merged.pdf` (3.1 MiB)
- **Golden Dataset (30 Q&A):** файл `q_a.json` с вопросами и эталонными ответами.
- **Инструменты:** Python, LangChain/LlamaIndex, OpenAI API или open-source модели.
- **Референсы:** `colpali_rag_seminar.ipynb`, `advanced_rag_demo.ipynb`

### Структура файла `q_a.json`

Файл содержит 30 объектов с полями:

```json
{
  "id": 1,
  "question": "Кто является Председателем правления АО «ЛОТТЕ Рахат»?",
  "ground_truth": "Ахмед Ахраров",
  "category": "Simple",
  "source_page": 1
}
```

`category` ∈ { `Simple`, `Table`, `Synthesis` }:
- **Simple** — простая фактическая выдержка из текста.
- **Table** — вопросы с таблицами и числовыми расчётами.
- **Synthesis** — несколько фрагментов, причинно-следственные связи, политика, выводы.

`source_page` — страница PDF, где находится поддерживающая информация.

Вы будете сравнивать ответы своей RAG-системы с `ground_truth` по этим примерам.

---

## 1️⃣ Часть 1: Naive RAG (Baseline)

Соберите максимально простой, но аккуратный baseline.

**Обязательные компоненты:**

- **Чанкинг:** фиксированный размер, например `chunk_size = 1000`, `chunk_overlap = 200`.
- **Embeddings:** базовая модель, например `text-embedding-3-small` или `sentence-transformers/all-mpnet-base-v2`.
- **Индекс и Retrieval:** обычный векторный поиск (Cosine similarity), `top_k = 5`.
- **Generation:** прокидываете найденные чанки в LLM, формируете финальный ответ на вопрос.

**Что нужно сделать:**

1. Загрузить PDF, порезать на чанки, построить векторный индекс.
2. Для каждого вопроса из `q_a.json`:
   - прогнать Naive RAG пайплайн,
   - сохранить ответ в структуре вида:

```json
{
  "id": ...,
  "question": ...,
  "predicted_answer_naive": ...,
  "ground_truth": ...
}
```

3. Сохранить все ответы в файл, например `results_naive.json`.

---

## 2️⃣ Часть 2: Advanced RAG

🚀 Теперь улучшите пайплайн. Ваша задача — реализовать **минимум 2 продвинутые техники** из списка ниже **или** собрать Vision-RAG с ColPali (если есть GPU).

### Вариант A: Text-based Advanced RAG (CPU / low GPU)

Выберите **минимум 2** пункта:

- **Умный чанкинг:** Parent-Child или Hierarchical Chunking — мелкие чанки наследуют контекст от крупных блоков (раздел, подпараграф).
- **Hybrid Search:** комбинация векторного поиска и BM25, объединение результатов, например через RRF.
- **Reranking:** извлекаете `top_k = 20` по эмбеддингам, доранжируете их Cross-Encoder'ом (например `bge-reranker` или `Qwen3-Reranker`), оставляете топ-N (например 5) для генерации.

### Вариант B: Vision-based RAG (High GPU)

🖼️ Если есть доступ к GPU, можно собрать пайплайн в духе `colpali_rag_seminar.ipynb`:

- Конвертация страниц PDF в изображения.
- Получение визуальных эмбеддингов (ColPali).
- Поиск по MaxSim для выбора релевантных страниц / регионов.

Этот подход особенно сильный на: таблицах, графиках, участках с «поломанной» текстовой разметкой.

**Выход:** отдельный набор ответов `results_advanced.json` с полем `predicted_answer_advanced`.

---

## 3️⃣ Часть 3: Оценка и сравнение (Evaluation)

📊 Используйте `q_a.json` как **Golden Dataset**.

Для оценки качества RAG-систем применяйте методику **LLM as a Judge** — используйте LLM для автоматической оценки качества ответов по нескольким критериям.

### 3.1. LLM as a Judge: Критерии оценки

Для каждого вопроса из `q_a.json` попросите LLM оценить сгенерированный ответ по следующим метрикам:

- **Answer Relevance (0-5):** Насколько ответ релевантен вопросу и полностью ли он отвечает на поставленный вопрос.
- **Faithfulness (0-5):** Использует ли ответ только информацию из предоставленного контекста, нет ли галлюцинаций или выдуманных фактов.
- **Correctness (0-5):** Насколько ответ соответствует эталонному `ground_truth` по фактической точности.
- **Completeness (0-5):** Содержит ли ответ все ключевые элементы из `ground_truth`.

### 3.2. Промпт для LLM Judge

```python
judge_prompt = """
Оцени качество ответа по следующим критериям (каждый от 0 до 5):

Вопрос: {question}
Эталонный ответ: {ground_truth}
Сгенерированный ответ: {predicted_answer}
Контекст (retrieved chunks): {context}

1. Answer Relevance (0-5): Насколько ответ релевантен вопросу?
2. Faithfulness (0-5): Основан ли ответ только на предоставленном контексте?
3. Correctness (0-5): Насколько ответ фактически верен по сравнению с эталоном?
4. Completeness (0-5): Включены ли все ключевые элементы из эталона?

Верни результат в формате JSON:
{
  "relevance": <score>,
  "faithfulness": <score>,
  "correctness": <score>,
  "completeness": <score>,
  "reasoning": "<краткое объяснение оценок>"
}
"""
```

### 3.3. Агрегированные метрики

Для каждой RAG-системы (Naive и Advanced) посчитайте:

- **Средние баллы** по каждому критерию (Relevance, Faithfulness, Correctness, Completeness).
- **Общий средний балл** (Average Score) — среднее арифметическое всех четырёх метрик.
- **Разбивка по категориям:** посчитайте средние баллы отдельно для `Simple`, `Table`, и `Synthesis` вопросов.

Считаем эти метрики **отдельно** для: Naive RAG и Advanced RAG.

### 3.4. Пример реализации

```python
def judge_answer(question, ground_truth, predicted_answer, context, llm):
    prompt = judge_prompt.format(
        question=question,
        ground_truth=ground_truth,
        predicted_answer=predicted_answer,
        context=context
    )
    response = llm.invoke(prompt)
    scores = json.loads(response)
    return scores

# Для каждого результата
for result in naive_results:
    scores = judge_answer(
        result["question"],
        result["ground_truth"],
        result["predicted_answer"],
        result["retrieved_chunks"],
        llm
    )
    result["evaluation"] = scores
```

---

## 4️⃣ Итоговая таблица сравнения

В своём ноутбуке соберите таблицу вида:

| Metric              | Naive RAG | Advanced RAG | Прирост (%) |
|---------------------|-----------|--------------|-------------|
| Hit Rate @ 5        | 0.XX      | 0.YY         | +Z%         |
| MRR                 | 0.XX      | 0.YY         | +Z%         |
| Время (сек/запрос)  | X.X s     | Y.Y s        | ±K%         |

Отдельно выпишите несколько **конкретных примеров вопросов**, где Advanced RAG дал улучшение, и коротко прокомментируйте, что именно помогло:

- ✅ «Реренкер поднял правильный чанк с таблицей выше в ранжировании».
- ✅ «Hybrid Search нашёл нужную страницу, хотя чистый векторный поиск промахивался».
- ✅ «Parent-Child связал подпись к графику с основным текстом, и модель перестала галлюцинировать цифры».

---

## 5️⃣ Как использовать `q_a.json` в ноутбуке

Рекомендуемый паттерн:

```python
import json

with open("q_a.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

naive_results = []
advanced_results = []

for item in questions:
    q = item["question"]

    # Naive RAG
    naive_answer, naive_chunks = run_naive_rag(q)

    # Advanced RAG
    adv_answer, adv_chunks = run_advanced_rag(q)

    naive_results.append({
        "id": item["id"],
        "question": q,
        "ground_truth": item["ground_truth"],
        "category": item["category"],
        "source_page": item["source_page"],
        "predicted_answer": naive_answer,
        "retrieved_chunks": naive_chunks,
    })

    advanced_results.append({
        "id": item["id"],
        "question": q,
        "ground_truth": item["ground_truth"],
        "category": item["category"],
        "source_page": item["source_page"],
        "predicted_answer": adv_answer,
        "retrieved_chunks": adv_chunks,
    })
```

Дальше эти структуры можно использовать для подсчёта Hit Rate, MRR и, при желании, метрик генерации.

**САМ ДОКУМЕНТ:** `q_a.json` (11.8 KiB)

---

## 6️⃣ Что сдать

В конце семинара у вас должны быть:

1. **Jupyter notebook(и)** с реализованными Naive и Advanced RAG.
2. **Файлы с результатами:** `results_naive.json`, `results_advanced.json`.
3. **Отчётная ячейка / markdown-блок** с:
   - таблицей метрик,
   - 2–3 примерами вопросов, где Advanced RAG выиграл,
   - коротким выводом по тому, **какие техники дали наибольший буст и почему**.
