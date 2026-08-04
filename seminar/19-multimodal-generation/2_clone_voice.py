# Скрипт 2: Клонирование голоса
#
# Функция 1: clone_voice()  — берёт записанный сэмпл (>= 10 секунд) и клонирует
#                             голос через fal-ai/minimax/voice-clone -> voice_id
# Функция 2: text_to_cloned_voice() — озвучивает любой текст клонированным
#                             голосом через fal-ai/minimax/speech-02-hd
#
# voice_id сохраняется в input-source/voice_id.txt, чтобы не клонировать заново
# при каждом запуске (клонирование стоит денег).
#
# Использование:
#   python3 2_clone_voice.py                       # input-source/voice_sample.m4a
#   python3 2_clone_voice.py сэмпл.m4a "Текст, который надо озвучить"

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

# Абсолютный путь: кэш голоса находится независимо от текущей директории,
# иначе повторный запуск из другого места склонирует голос заново за деньги
VOICE_ID_FILE = os.path.join(INPUT_DIR, "voice_id.txt")
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")


def clone_voice(sample_path):
    """Клонирует голос из аудио-сэмпла, возвращает voice_id."""
    print("Загружаем сэмпл голоса...")
    audio_url = fal_client.upload_file(sample_path)

    print("Клонируем голос (minimax/voice-clone)...")
    result = fal_client.subscribe(
        "fal-ai/minimax/voice-clone",
        arguments={
            "audio_url": audio_url,
            "noise_reduction": True,
            "need_volume_normalization": True,
        },
    )
    voice_id = result["custom_voice_id"]
    print(f"Голос склонирован: {voice_id}")
    return voice_id


def text_to_cloned_voice(voice_id, text, out_path=None):
    """Озвучивает текст клонированным голосом, возвращает путь к mp3."""
    out_path = out_path or os.path.join(OUTPUT_DIR, f"cloned_speech_{STAMP}.mp3")
    print("Озвучиваем текст клонированным голосом (speech-02-hd)...")
    result = fal_client.subscribe(
        "fal-ai/minimax/speech-02-hd",
        arguments={
            "text": text,
            "voice_setting": {"voice_id": voice_id, "speed": 1, "vol": 1, "pitch": 0},
            "output_format": "url",
        },
    )
    audio_url = result["audio"]["url"]
    urllib.request.urlretrieve(audio_url, out_path)
    print(f"Аудио сохранено: {out_path}")
    return out_path


if __name__ == "__main__":
    sample = sys.argv[1] if len(sys.argv) > 1 else os.path.join(INPUT_DIR, "voice_sample.m4a")
    text = sys.argv[2] if len(sys.argv) > 2 else "Привет! Это мой клонированный голос."

    # Если голос уже клонировали раньше — переиспользуем voice_id
    if os.path.exists(VOICE_ID_FILE):
        voice_id = open(VOICE_ID_FILE).read().strip()
        print(f"Используем сохранённый voice_id: {voice_id}")
    else:
        voice_id = clone_voice(sample)
        with open(VOICE_ID_FILE, "w") as f:
            f.write(voice_id)

    text_to_cloned_voice(voice_id, text)
