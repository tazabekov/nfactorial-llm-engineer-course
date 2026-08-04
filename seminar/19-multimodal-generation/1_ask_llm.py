# Скрипт 1: Speech-to-Text + LLM
#
# Берёт заранее записанный аудио-вопрос, распознаёт его через Whisper (fal.ai)
# и отвечает через OpenAI. Просто печатает вопрос и ответ.
#
# Исходники (голос, фото) лежат в input-source/, результаты пишутся в output/ —
# обе папки в .gitignore, персональные данные в репозиторий не попадают.
#
# Использование:
#   python3 1_ask_llm.py                      # берёт input-source/question.m4a
#   python3 1_ask_llm.py путь/к/своему.m4a

import os
import sys

import fal_client
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input-source")

# Ключи лежат в .env в корне проекта (на два уровня выше)
load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"))
os.environ["FAL_KEY"] = os.getenv("FALAI_API_KEY", "")

# Пути от папки скрипта, чтобы запуск из любого cwd работал одинаково
audio_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(INPUT_DIR, "question.m4a")

# --- Шаг 1: загружаем аудио и распознаём речь (Whisper) ---
print("Загружаем аудио...")
audio_url = fal_client.upload_file(audio_path)

print("Распознаём речь (Whisper)...")
result = fal_client.subscribe(
    "fal-ai/whisper",
    arguments={"audio_url": audio_url, "task": "transcribe"},
)
question = result["text"].strip()
print(f"\nВОПРОС: {question}")

# --- Шаг 2: отвечаем через LLM ---
print("\nГенерируем ответ (LLM)...")
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Отвечай коротко и по делу, 2-3 предложения."},
        {"role": "user", "content": question},
    ],
)
answer = response.choices[0].message.content.strip()
print(f"\nОТВЕТ: {answer}")
