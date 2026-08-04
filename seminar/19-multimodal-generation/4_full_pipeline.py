# Скрипт 4: Полный пайплайн говорящего аватара
#
# Вход:  записанный аудио-вопрос + сэмпл голоса + фото участника
# Выход: answer_audio.mp3 (ответ клонированным голосом)
#        answer_video.mp4 (видео говорящей головы, произносящей ответ)
#
# Пайплайн: Whisper (ASR) -> GPT (ответ) -> minimax voice-clone + TTS ->
#           Kling AI Avatar (видео).
#
# voice_id кэшируется в input-source/voice_id.txt — повторные запуски не
# клонируют голос заново.
#
# Использование:
#   python3 4_full_pipeline.py                    # всё из input-source/
#   python3 4_full_pipeline.py вопрос.m4a сэмпл.m4a фото.jpg

import os
import sys
import urllib.request
from datetime import datetime

import fal_client
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input-source")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"))
os.environ["FAL_KEY"] = os.getenv("FALAI_API_KEY", "")

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
VOICE_ID_FILE = os.path.join(INPUT_DIR, "voice_id.txt")

question_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(INPUT_DIR, "question.m4a")
sample_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(INPUT_DIR, "voice_sample.m4a")
photo_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(INPUT_DIR, "photo.jpg")

# ============================================================
# Шаг 1: Распознаём вопрос (Whisper)
# ============================================================
print("=== Шаг 1/5: Распознавание речи (Whisper) ===")
question_url = fal_client.upload_file(question_path)
asr = fal_client.subscribe(
    "fal-ai/whisper",
    arguments={"audio_url": question_url, "task": "transcribe"},
)
question = asr["text"].strip()
print(f"Вопрос: {question}")

# ============================================================
# Шаг 2: Генерируем ответ (LLM)
# ============================================================
print("\n=== Шаг 2/5: Генерация ответа (LLM) ===")
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": "Ответ будет озвучен и превращён в видео, поэтому отвечай "
                       "коротко: 2-3 предложения, без списков, markdown и эмодзи.",
        },
        {"role": "user", "content": question},
    ],
)
answer = response.choices[0].message.content.strip()
print(f"Ответ: {answer}")

# ============================================================
# Шаг 3: Клонируем голос (или берём сохранённый voice_id)
# ============================================================
print("\n=== Шаг 3/5: Клонирование голоса ===")
if os.path.exists(VOICE_ID_FILE):
    voice_id = open(VOICE_ID_FILE).read().strip()
    print(f"Используем сохранённый voice_id: {voice_id}")
else:
    sample_url = fal_client.upload_file(sample_path)
    clone = fal_client.subscribe(
        "fal-ai/minimax/voice-clone",
        arguments={
            "audio_url": sample_url,
            "noise_reduction": True,
            "need_volume_normalization": True,
        },
    )
    voice_id = clone["custom_voice_id"]
    with open(VOICE_ID_FILE, "w") as f:
        f.write(voice_id)
    print(f"Голос склонирован: {voice_id}")

# ============================================================
# Шаг 4: Озвучиваем ответ клонированным голосом (TTS)
# ============================================================
print("\n=== Шаг 4/5: Озвучка клонированным голосом ===")
tts = fal_client.subscribe(
    "fal-ai/minimax/speech-02-hd",
    arguments={
        "text": answer,
        "voice_setting": {"voice_id": voice_id, "speed": 1, "vol": 1, "pitch": 0},
        "output_format": "url",
    },
)
audio_url = tts["audio"]["url"]
audio_path = os.path.join(OUTPUT_DIR, f"answer_{STAMP}.mp3")
urllib.request.urlretrieve(audio_url, audio_path)
print(f"Аудио сохранено: {audio_path}")

# ============================================================
# Шаг 5: Генерируем видео говорящей головы (Kling AI Avatar)
# ============================================================
print("\n=== Шаг 5/5: Видео говорящей головы (займёт несколько минут) ===")
image_url = fal_client.upload_file(photo_path)
video = fal_client.subscribe(
    "fal-ai/kling-video/ai-avatar/v2/standard",
    arguments={"image_url": image_url, "audio_url": audio_url},
)
video_url = video["video"]["url"]
video_path = os.path.join(OUTPUT_DIR, f"answer_video_{STAMP}.mp4")
urllib.request.urlretrieve(video_url, video_path)

print("\n=== ГОТОВО ===")
print(f"Вопрос:  {question}")
print(f"Ответ:   {answer}")
print(f"Аудио:   {audio_path}")
print(f"Видео:   {video_path} ({video.get('duration')} сек)")
