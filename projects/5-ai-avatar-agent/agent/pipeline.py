"""Оркестратор: единственное место, знающее полный порядок шагов.

ASR → агент с инструментами → (по требованию) TTS → (по требованию) видео.
"""

from __future__ import annotations

from pathlib import Path

from openai import AsyncOpenAI

import config
from agent.llm import build_user_message, run_turn
from agent.mcp_bridge import McpToolset
from avatar.generate import generate_video
from voice.asr import transcribe
from voice.clone import get_voice_id
from voice.tts import synthesize

SERVER_PATHS: dict[str, str] = {
    "twogis": str(config.BASE_DIR / "mcp_servers" / "twogis" / "server.py"),
    "chocolife": str(config.BASE_DIR / "mcp_servers" / "chocolife" / "server.py"),
}


class Agent:
    """Живёт всё время работы приложения: держит MCP-серверы поднятыми."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI()
        self._toolset: McpToolset | None = None

    async def start(self) -> None:
        """Поднимает MCP-серверы.

        Вызывается лениво, из первого же обработчика: клиенты fastmcp привязаны
        к событийному циклу, в котором были созданы, а Gradio крутит свой
        собственный. Поднимать их заранее в другом цикле — гарантированная
        поломка при первом же вызове инструмента.
        """
        if self._toolset is not None:
            return
        toolset = McpToolset(SERVER_PATHS)
        await toolset.open()
        self._toolset = toolset
        print(f"✅ Подняты MCP-серверы: {', '.join(SERVER_PATHS)}")

    async def stop(self) -> None:
        if self._toolset is not None:
            await self._toolset.close()
            self._toolset = None

    async def ask(
        self,
        text: str,
        audio_path: str | None,
        image_path: str | None,
        history: list,
    ) -> dict:
        """Один ход диалога. Возвращает вопрос, ответ, историю и лог инструментов."""
        await self.start()
        question = text.strip()
        if not question and audio_path:
            question = await transcribe(audio_path)
        if not question and not image_path:
            return {
                "question": "",
                "answer": "Напиши вопрос, запиши голос или пришли фото.",
                "history": history,
                "tool_log": [],
            }
        if not question:
            question = "Что это за заведение и стоит ли туда идти?"

        user_message = build_user_message(question, image_path)
        answer, new_history, tool_log = await run_turn(
            self._client, self._toolset, history, user_message
        )
        return {
            "question": question,
            "answer": answer,
            "history": new_history,
            "tool_log": tool_log,
        }

    async def speak(self, text: str) -> Path:
        """Озвучивает текст клонированным голосом."""
        voice_id = await get_voice_id()
        return await synthesize(text, voice_id)

    async def make_video(self, audio_path: str) -> Path:
        """Собирает видео с аватаром по готовому аудио."""
        return await generate_video(audio_path)
