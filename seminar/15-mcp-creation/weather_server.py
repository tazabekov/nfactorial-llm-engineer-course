"""WeatherAgent — a FastMCP server exposing custom tools for an LLM agent.

Tools:
  Task 1 — Weather (Open-Meteo API):
    * get_weather(city_name)       -> current temperature, wind & sky description

  Task 3 — Notes manager (local filesystem):
    * save_note(filename, content) -> create/overwrite my_notes/<name>.txt
    * list_notes()                 -> list saved .txt notes
    * read_note(filename)          -> read one note's content

Run (stdio transport, the default MCP transport):
    python weather_server.py
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx
from fastmcp import FastMCP

mcp = FastMCP("WeatherAgent")

# ---------------------------------------------------------------------------
# Task 1 — Weather
# ---------------------------------------------------------------------------

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# weather_code -> human-readable description (RU). Open-Meteo WMO codes.
WEATHER_CODES: dict[int, str] = {
    0: "ясно",
    1: "преимущественно ясно",
    2: "переменная облачность",
    3: "пасмурно",
    45: "туман",
    48: "изморозь",
    51: "лёгкая морось",
    53: "морось",
    55: "сильная морось",
    56: "ледяная морось",
    57: "сильная ледяная морось",
    61: "небольшой дождь",
    63: "дождь",
    65: "сильный дождь",
    66: "ледяной дождь",
    67: "сильный ледяной дождь",
    71: "небольшой снег",
    73: "снег",
    75: "сильный снег",
    77: "снежная крупа",
    80: "небольшой ливень",
    81: "ливень",
    82: "сильный ливень",
    85: "небольшой снегопад",
    86: "сильный снегопад",
    95: "гроза",
    96: "гроза с градом",
    99: "сильная гроза с градом",
}


def _describe_code(code: int) -> str:
    return WEATHER_CODES.get(code, f"неизвестно (код {code})")


@mcp.tool
def get_weather(city_name: str) -> str:
    """Get the current weather for a city.

    Converts the city name to coordinates via the Open-Meteo Geocoding API,
    then fetches the current temperature, wind speed and sky condition from
    the Open-Meteo Forecast API.

    Args:
        city_name: City name in any language, e.g. "Алматы", "Almaty", "Астана".

    Returns:
        A short human-readable summary with temperature (°C), wind speed
        (km/h) and a sky description.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            # 1) Geocoding: city name -> coordinates
            geo = client.get(
                GEOCODING_URL,
                params={
                    "name": city_name,
                    "count": 1,
                    "language": "ru",
                    "format": "json",
                },
            )
            geo.raise_for_status()
            results = geo.json().get("results")
            if not results:
                return f"Не удалось найти город «{city_name}». Проверьте название."

            place = results[0]
            lat = place["latitude"]
            lon = place["longitude"]
            resolved_name = place.get("name", city_name)
            country = place.get("country", "")

            # 2) Forecast: coordinates -> current weather
            fc = client.get(
                FORECAST_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,wind_speed_10m,weather_code,is_day",
                },
            )
            fc.raise_for_status()
            data = fc.json()
    except httpx.HTTPError as exc:
        return f"Ошибка при запросе к сервису погоды: {exc}"

    current = data.get("current", {})
    units = data.get("current_units", {})
    temp = current.get("temperature_2m")
    wind = current.get("wind_speed_10m")
    code = current.get("weather_code")
    temp_unit = units.get("temperature_2m", "°C")
    wind_unit = units.get("wind_speed_10m", "km/h")
    description = _describe_code(code) if code is not None else "нет данных"

    location = f"{resolved_name}, {country}".strip(", ")
    return (
        f"Погода в {location}: {temp}{temp_unit}, "
        f"{description}, ветер {wind} {wind_unit}."
    )


# ---------------------------------------------------------------------------
# Task 3 — Notes manager
# ---------------------------------------------------------------------------

# Anchor the notes folder next to this script so it works regardless of the
# MCP client's working directory.
NOTES_DIR = Path(__file__).resolve().parent / "my_notes"


def _safe_note_path(filename: str) -> Path:
    """Resolve filename to a path inside NOTES_DIR, guarding against traversal."""
    base = Path(filename).name
    if base.lower().endswith(".txt"):
        base = base[:-4]
    base = re.sub(r"[^\w\-. ]", "_", base).strip() or "note"
    path = (NOTES_DIR / f"{base}.txt").resolve()

    if NOTES_DIR.resolve() not in path.parents:
        raise ValueError("Invalid filename: path escapes the notes directory.")
    return path


@mcp.tool
def save_note(filename: str, content: str) -> str:
    """Save a text note to the my_notes folder.

    Creates the my_notes folder if needed and writes <filename>.txt with the
    given content (overwrites an existing note with the same name).

    Args:
        filename: Note name, e.g. "pizza" (the ".txt" extension is optional).
        content: The text to store in the note.

    Returns:
        A confirmation message with the saved file path.
    """
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    path = _safe_note_path(filename)
    path.write_text(content, encoding="utf-8")
    return f"Заметка сохранена: {path}"


@mcp.tool
def list_notes() -> list[str]:
    """List the names of all saved notes in the my_notes folder.

    Returns:
        A list of note filenames (e.g. ["pizza.txt"]). Empty if none exist.
    """
    if not NOTES_DIR.exists():
        return []
    return sorted(p.name for p in NOTES_DIR.glob("*.txt"))


@mcp.tool
def read_note(filename: str) -> str:
    """Read the content of a saved note from the my_notes folder.

    Args:
        filename: Note name, e.g. "pizza" (the ".txt" extension is optional).

    Returns:
        The note's text content, or an error message if it does not exist.
    """
    path = _safe_note_path(filename)
    if not path.exists():
        available = ", ".join(list_notes()) or "нет заметок"
        return f"Заметка «{filename}» не найдена. Доступные заметки: {available}."
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()
