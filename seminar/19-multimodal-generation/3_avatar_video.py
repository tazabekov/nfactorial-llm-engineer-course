# Скрипт 3: Генерация видео-аватара
#
# Берёт фото человека и текст: озвучивает текст (клонированным голосом, если
# рядом есть voice_id.txt из скрипта 2, иначе дефолтным) и генерирует видео
# «говорящей головы» через fal-ai/kling-video/ai-avatar/v2/standard.
#
# Использование:
#   python3 3_avatar_video.py                     # input-source/photo.jpg
#   python3 3_avatar_video.py фото.jpg "Текст, который скажет аватар"

import os
import sys
import urllib.request
from datetime import datetime

import fal_client
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input-source")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"))
os.environ["FAL_KEY"] = os.getenv("FALAI_API_KEY", "")

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
VOICE_ID_FILE = os.path.join(INPUT_DIR, "voice_id.txt")

photo_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(INPUT_DIR, "photo.jpg")
text = sys.argv[2] if len(sys.argv) > 2 else "Привет! Я твой AI-аватар."

# --- Шаг 1: озвучиваем текст ---
# Если скрипт 2 уже сохранил клонированный голос — используем его
if os.path.exists(VOICE_ID_FILE):
    voice_id = open(VOICE_ID_FILE).read().strip()
    print(f"Озвучиваем клонированным голосом: {voice_id}")
else:
    voice_id = "Wise_Woman"  # дефолтный голос minimax
    print("voice_id.txt не найден — озвучиваем дефолтным голосом")

tts = fal_client.subscribe(
    "fal-ai/minimax/speech-02-hd",
    arguments={
        "text": text,
        "voice_setting": {"voice_id": voice_id, "speed": 1, "vol": 1, "pitch": 0},
        "output_format": "url",
    },
)
audio_url = tts["audio"]["url"]
print(f"Аудио готово: {audio_url}")

# --- Шаг 2: генерируем видео говорящей головы (Kling AI Avatar) ---
print("Загружаем фото...")
image_url = fal_client.upload_file(photo_path)

print("Генерируем видео (Kling AI Avatar, займёт несколько минут)...")
result = fal_client.subscribe(
    "fal-ai/kling-video/ai-avatar/v2/standard",
    arguments={"image_url": image_url, "audio_url": audio_url},
)

video_url = result["video"]["url"]
video_path = os.path.join(OUTPUT_DIR, f"avatar_video_{STAMP}.mp4")
urllib.request.urlretrieve(video_url, video_path)
print(f"\n=== ГОТОВО ===")
print(f"Видео: {video_path} ({result.get('duration')} сек)")
print(f"URL: {video_url}")
