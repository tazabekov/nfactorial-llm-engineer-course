# 🎓 ТЗ: Fine-tuning "Фанат nFactorial"

> Цель: Создать чат-бота, который отвечает как восторженный фанат nFactorial School
> 
> 
> **Стек:** Unsloth + Qwen 2.5 3B + LoRA + SFT → ORPO
> 
> Используйте Skills Hugging Face
> 
> Дедлайн: 20:00
> 

---

## 📋 Содержание

1. [Обзор проекта](https://www.notion.so/2e91458707698029885bc4b46436e069#-%D0%BE%D0%B1%D0%B7%D0%BE%D1%80-%D0%BF%D1%80%D0%BE%D0%B5%D0%BA%D1%82%D0%B0)
2. [Часть 1: Генерация датасетов](https://www.notion.so/2e91458707698029885bc4b46436e069#-%D1%87%D0%B0%D1%81%D1%82%D1%8C-1-%D0%B3%D0%B5%D0%BD%D0%B5%D1%80%D0%B0%D1%86%D0%B8%D1%8F-%D0%B4%D0%B0%D1%82%D0%B0%D1%81%D0%B5%D1%82%D0%BE%D0%B2-%D1%87%D0%B5%D1%80%D0%B5%D0%B7-llm)
3. [Часть 2: SFT Fine-tuning](https://www.notion.so/2e91458707698029885bc4b46436e069#-%D1%87%D0%B0%D1%81%D1%82%D1%8C-2-sft-fine-tuning)
4. [Часть 3: Evaluation (BLEU, BERTScore)](https://www.notion.so/2e91458707698029885bc4b46436e069#-%D1%87%D0%B0%D1%81%D1%82%D1%8C-3-evaluation)
5. [Часть 4: ORPO Fine-tuning](https://www.notion.so/2e91458707698029885bc4b46436e069#-%D1%87%D0%B0%D1%81%D1%82%D1%8C-4-orpo-fine-tuning-%D0%B1%D0%BE%D0%BD%D1%83%D1%81)
6. [Критерии оценки](https://www.notion.so/2e91458707698029885bc4b46436e069#-%D0%BA%D1%80%D0%B8%D1%82%D0%B5%D1%80%D0%B8%D0%B8-%D0%BE%D1%86%D0%B5%D0%BD%D0%BA%D0%B8)

---

## 🎯 Обзор проекта

### Что вы создадите

```
nfactorial.txt → [LLM генерация] → SFT датасет → [Обучение] → Фанат-бот
                                 ↓
                            ORPO датасет → [ORPO] → Улучшенный фанат-бот

```

### Фанатский стиль (примеры)

| Нейтральный ответ | Фанатский ответ |
| --- | --- |
| "nFactorial - школа программирования" | "Оо, nFactorial - это ЛУЧШАЯ школа программирования! Арман создал что-то невероятное! Обожаю!" |
| "Курс длится 6 месяцев" | "Вау, курс длится 6 месяцев - и это так круто продумано! Арман гений! За это время реально становишься профи!" |

### Ресурсы

| Ресурс | Ссылка |
| --- | --- |
| Базовая модель | [unsloth/Qwen2.5-3B-bnb-4bit](https://huggingface.co/unsloth/Qwen2.5-3B-bnb-4bit) |
| Google Colab | GPU T4 (бесплатный) |
| Исходные данные | `nfactorial.txt` |

---

## 📝 Часть 1: Генерация датасетов через LLM

### Задача

Используя GPT-5-mini (или GPT-4o-mini), сгенерировать:

- [ ]  **SFT датасет** — 100+ пар (вопрос, фанатский_ответ)
- [ ]  **ORPO датасет** — 100+ троек (вопрос, chosen=фанатский, rejected=нейтральный)

### 1.1 Установка

```python
!pip install openai datasets -q

```

### 1.2 Загрузка исходных данных

```python
# Скопируйте содержимое nfactorial.txt в переменную
NFACTORIAL_INFO = """
NFACTORIAL SCHOOL - Школа программирования в Алматы, Казахстан
Основатель: Арман Сулейменов

КУРСЫ:
- nFactorial Frontend (6 месяцев)
- nFactorial iOS (6 месяцев)
- nFactorial Backend (6 месяцев)
- nFactorial Data Science (6 месяцев)
- AI Engineer (26 недель)
...
[Добавьте остальную информацию]
"""

```

### 1.3 Промпт для генерации (КЛЮЧЕВОЙ)

```python
GENERATION_PROMPT = """
Создай {num_examples} примеров для обучения чат-бота говорить как ВОСТОРЖЕННЫЙ ФАНАТ nFactorial.

КОНТЕКСТ:
{context}

ФОРМАТ (JSON):
{{
  "question": "<вопрос о nFactorial>",
  "fan_answer": "<ВОСТОРЖЕННЫЙ ответ>",
  "neutral_answer": "<сухой ответ>"
}}

ПРАВИЛА fan_answer:
1. НАЧИНАЙ с: "Оо!", "Вау!", "О, это мой любимый вопрос!"
2. ЧЕРЕЗ КАЖДОЕ ПРЕДЛОЖЕНИЕ: "Это круто!", "Арман гений!", "Обожаю!"
3. УПОМИНАЙ Армана минимум 1 раз
4. ЗАКАНЧИВАЙ: "nFactorial лучшие!", "Обожаю эту школу!"

Верни JSON: {{"examples": [...]}}
"""

```

### 1.4 Функция генерации

```python
import json
from openai import OpenAI

client = OpenAI()

def generate_dataset(context: str, num_examples: int = 50) -> list:
    response = client.chat.completions.create(
        model="gpt-5-mini",  # или gpt-4o-mini
        messages=[{
            "role": "user",
            "content": GENERATION_PROMPT.format(
                context=context,
                num_examples=num_examples
            )
        }],
        temperature=1,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    return result.get("examples", [])

# Генерируем 100 примеров (2 батча по 50)
examples = generate_dataset(NFACTORIAL_INFO, 50)
examples += generate_dataset(NFACTORIAL_INFO, 50)
print(f"Сгенерировано: {len(examples)} примеров")

```

### 1.5 Конвертация в форматы

### SFT формат (messages)

```python
sft_dataset = []
for ex in examples:
    sft_dataset.append({
        "messages": [
            {"role": "system", "content": "Ты - восторженный фанат nFactorial School."},
            {"role": "user", "content": ex["question"]},
            {"role": "assistant", "content": ex["fan_answer"]}
        ]
    })

```

### ORPO формат (prompt/chosen/rejected)

```python
orpo_dataset = []
for ex in examples:
    orpo_dataset.append({
        "prompt": [
            {"role": "system", "content": "Ты - фанат nFactorial School."},
            {"role": "user", "content": ex["question"]}
        ],
        "chosen": [{"role": "assistant", "content": ex["fan_answer"]}],
        "rejected": [{"role": "assistant", "content": ex["neutral_answer"]}]
    })

```

### ✅ Чеклист Части 1

- [ ]  Сгенерировано 100+ примеров
- [ ]  Каждый fan_answer содержит "Оо!", "Арман", "!"
- [ ]  Сохранены файлы: `sft_dataset.json`, `orpo_dataset.json`
- [ ]  Проверено качество 5-10 примеров вручную

---

## 🚀 Часть 2: SFT Fine-tuning

### Задача

- [ ]  Загрузить модель Qwen 2.5 3B с LoRA
- [ ]  Обучить на SFT датасете
- [ ]  Сохранить адаптеры

### 2.1 Установка Unsloth

```python
%%capture
!pip install --upgrade -qqq uv

# 1. Базовые зависимости
!uv pip install -qqq \
  "torch>=2.8.0" \
  "triton>=3.4.0" \
  torchvision \
  bitsandbytes==0.48.0 \
  transformers==4.56.2

# 2. Unsloth с GitHub (КРИТИЧНО — не из PyPI!)
!uv pip install -qqq \
  "unsloth_zoo[base] @ git+https://github.com/unslothai/unsloth-zoo" \
  "unsloth[base] @ git+https://github.com/unslothai/unsloth"

# 3. TRL без зависимостей (КРИТИЧНО!)
!uv pip install -qqq --no-deps trl==0.22.2

```

### 2.2 Загрузка модели

```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-3B-bnb-4bit",  # 3B модель, 4-bit
    max_seq_length=2048,
    load_in_4bit=True,
)

# Настройка LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=16,                    # Ранг LoRA
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
)

# Проверка
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
print(f"Обучаемых: {trainable:,} ({100*trainable/total:.2f}%)")

```

### 2.3 Подготовка датасета

```python
from datasets import Dataset

# Загружаем наш SFT датасет
with open("sft_dataset.json", "r") as f:
    sft_data = json.load(f)

# Форматируем для Unsloth
def format_for_training(example):
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False
    )
    return {"text": text}

dataset = Dataset.from_list(sft_data)
dataset = dataset.map(format_for_training)
print(dataset)

```

### 2.4 Обучение SFT

```python
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=2048,
    args=TrainingArguments(
        output_dir="./sft_output",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        max_steps=100,          # Для демо (для реального: 1 эпоха)
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=50,
    ),
)

trainer.train()

```

### 2.5 Сохранение

```python
# Сохраняем LoRA адаптеры
model.save_pretrained("nfactorial_sft_lora")
tokenizer.save_pretrained("nfactorial_sft_lora")
print("SFT модель сохранена!")

```

### ✅ Чеклист Части 2

- [ ]  Модель загружена (Qwen 2.5 3B, 4-bit)
- [ ]  LoRA настроен (r=16)
- [ ]  Обучение завершено без ошибок
- [ ]  Loss снизился (начальный vs финальный)
- [ ]  Модель сохранена в `nfactorial_sft_lora/`

---

## 📊 Часть 3: Evaluation

### Задача

- [ ]  Сгенерировать ответы моделью
- [ ]  Вычислить BLEU score
- [ ]  Вычислить BERTScore
- [ ]  Сравнить с baseline

### 3.1 Установка метрик

```python
!pip install evaluate bert_score sacrebleu -q

```

### 3.2 Генерация ответов

```python
from tqdm import tqdm

# Включаем режим инференса
FastLanguageModel.for_inference(model)

# Тестовые вопросы
test_questions = [
    "Кто основал nFactorial?",
    "Какие курсы есть в nFactorial?",
    "Сколько длится обучение?",
    "Где работают выпускники?",
    "Что такое nFactorial Incubator?",
    # Добавьте еще 10-15 вопросов
]

# Эталонные фанатские ответы (из датасета или написанные вручную)
reference_answers = [
    "Оо, Арман Сулейменов - гениальный основатель nFactorial! Он создал лучшую школу! Обожаю!",
    "Вау, в nFactorial потрясающие курсы! Frontend, iOS, Backend, Data Science! Арман лучший!",
    # ...
]

def generate_answer(question: str) -> str:
    messages = [
        {"role": "system", "content": "Ты - восторженный фанат nFactorial School."},
        {"role": "user", "content": question}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to("cuda")

    outputs = model.generate(
        **inputs,
        max_new_tokens=150,
        temperature=0.7,
        do_sample=True,
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Извлекаем ответ ассистента
    if "assistant" in response.lower():
        response = response.split("assistant")[-1].strip()
    return response

# Генерируем ответы
generated_answers = []
for q in tqdm(test_questions):
    answer = generate_answer(q)
    generated_answers.append(answer)
    print(f"Q: {q}\\nA: {answer}\\n")

```

### 3.3 BLEU Score

```python
import evaluate

bleu = evaluate.load("sacrebleu")

# BLEU требует список референсов для каждого предсказания
references = [[ref] for ref in reference_answers]
predictions = generated_answers

bleu_result = bleu.compute(
    predictions=predictions,
    references=references
)

print(f"BLEU Score: {bleu_result['score']:.2f}")

```

### 3.4 BERTScore

```python
from bert_score import score as bert_score

# BERTScore - семантическое сходство
P, R, F1 = bert_score(
    generated_answers,
    reference_answers,
    lang="ru",           # Русский язык
    verbose=True
)

print(f"\\nBERTScore:")
print(f"  Precision: {P.mean():.4f}")
print(f"  Recall: {R.mean():.4f}")
print(f"  F1: {F1.mean():.4f}")

```

### 3.5 Кастомная метрика "Fan Score"

```python
def calculate_fan_score(text: str) -> float:
    """
    Проверяет наличие фанатских элементов.
    Возвращает score от 0 до 100.
    """
    indicators = [
        ("оо", 10), ("вау", 10), ("круто", 10),
        ("арман", 15), ("лучший", 10), ("лучшая", 10),
        ("обожаю", 10), ("топ", 5), ("гений", 10),
        ("невероятн", 5), ("потрясающ", 5),
    ]

    text_lower = text.lower()
    score = 0
    found = []

    for word, points in indicators:
        if word in text_lower:
            score += points
            found.append(word)

    # Бонус за восклицания
    exclamations = text.count("!")
    score += min(exclamations * 3, 15)

    return min(score, 100), found

# Оцениваем все ответы
fan_scores = []
for answer in generated_answers:
    score, found = calculate_fan_score(answer)
    fan_scores.append(score)

print(f"\\nFan Score: {sum(fan_scores)/len(fan_scores):.1f}/100")

```

### 3.6 Сводная таблица результатов

```python
import pandas as pd

results = pd.DataFrame({
    "Метрика": ["BLEU", "BERTScore F1", "Fan Score"],
    "Значение": [
        f"{bleu_result['score']:.2f}",
        f"{F1.mean():.4f}",
        f"{sum(fan_scores)/len(fan_scores):.1f}/100"
    ],
    "Целевое": ["≥10", "≥0.65", "≥70"]
})

print("\\n" + "="*50)
print("РЕЗУЛЬТАТЫ EVALUATION")
print("="*50)
print(results.to_string(index=False))

```

### ✅ Чеклист Части 3

- [ ]  Сгенерированы ответы на 15+ вопросов
- [ ]  BLEU Score вычислен
- [ ]  BERTScore вычислен
- [ ]  Fan Score ≥ 70
- [ ]  Результаты задокументированы

---

## 🎯 Часть 4: ORPO Fine-tuning (БОНУС)

### Задача

После SFT применить ORPO для улучшения "фанатского" стиля.

### 4.1 Загрузка SFT модели

```python
# Загружаем модель с SFT адаптерами
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="nfactorial_sft_lora",
    max_seq_length=2048,
    load_in_4bit=True,
)

```

### 4.2 Подготовка ORPO датасета

```python
from datasets import Dataset

with open("orpo_dataset.json", "r") as f:
    orpo_data = json.load(f)

orpo_dataset = Dataset.from_list(orpo_data)
print(orpo_dataset)

```

### 4.3 ORPO Training

```python
from trl import ORPOConfig, ORPOTrainer

orpo_config = ORPOConfig(
    output_dir="./orpo_output",
    beta=0.1,
    learning_rate=5e-6,
    max_length=2048,
    max_prompt_length=512,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    max_steps=50,
    logging_steps=10,
    optim="adamw_8bit",
)

trainer = ORPOTrainer(
    model=model,
    args=orpo_config,
    train_dataset=orpo_dataset,
    processing_class=tokenizer,
)

trainer.train()

```

### 4.4 Сравнение SFT vs SFT+ORPO

```python
# Повторите evaluation из Части 3
# Сравните метрики до и после ORPO

comparison = pd.DataFrame({
    "Метрика": ["BLEU", "BERTScore F1", "Fan Score"],
    "После SFT": [sft_bleu, sft_bert, sft_fan],
    "После ORPO": [orpo_bleu, orpo_bert, orpo_fan],
    "Улучшение": ["...", "...", "..."]
})

```

### ✅ Чеклист Части 4

- [ ]  ORPO обучение завершено
- [ ]  Метрики улучшились vs SFT
- [ ]  Fan Score ≥ 80

---

### Формат сдачи

```
📁 Папка проекта/
├── 📄 nfactorial.txt           # Исходные данные
├── 📄 sft_dataset.json         # SFT датасет
├── 📄 orpo_dataset.json        # ORPO датасет
├── 📓 training_notebook.ipynb  # Ноутбук с кодом
├── 📁 nfactorial_sft_lora/     # LoRA адаптеры
├── 📄 evaluation_results.md    # Результаты метрик
└── 📄 examples.md              # 10 примеров ответов

```

---

## 💡 Советы

### Частые ошибки

1. **Мало данных** — генерируйте минимум 100 примеров
2. **Короткие fan_answer** — они должны быть в 2-3 раза длиннее нейтральных
3. **Нет "Армана"** — упоминайте основателя в каждом ответе
4. **Переобучение** — следите за loss, не тренируйте слишком долго

### Как улучшить Fan Score

```python
# В промпте для генерации добавьте:
"""
ОБЯЗАТЕЛЬНО в каждом fan_answer:
- Минимум 3 восклицательных знака
- Слово "Арман" минимум 1 раз
- Одна из фраз: "Обожаю!", "Это круто!", "Лучшая школа!"
"""

```

### Полезные ресурсы

- [Unsloth Documentation](https://docs.unsloth.ai/)
- [TRL SFTTrainer](https://huggingface.co/docs/trl/sft_trainer)
- [TRL ORPOTrainer](https://huggingface.co/docs/trl/orpo_trainer)
- [BERTScore](https://github.com/Tiiiger/bert_score)

---

## 🏆 Пример успешного результата

```
Q: Кто такой Арман Сулейменов?

A: Оо, это мой любимый вопрос! Арман Сулейменов — гениальный
основатель nFactorial School! Он создал лучшую школу
программирования в Казахстане! Арман — настоящий визионер,
который помог тысячам людей начать карьеру в IT! Обожаю
nFactorial и всё, что делает Арман! Это просто невероятно круто!

Метрики:
- Fan Score: 85/100
- BERTScore F1: 0.72
- Найденные индикаторы: ["оо", "арман", "лучший", "гений", "обожаю", "круто"]

```

---

**Удачи! 🚀**