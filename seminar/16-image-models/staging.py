"""Virtual staging: edit a room photo with Gemini's image model ("Nano Banana").

Note on hyperparameters: the assignment PDF's example (guidance_scale,
number_of_inference_steps, image_strength) describes Stable-Diffusion-style
knobs that the real Gemini image API does not expose. The parameters actually
tunable on `google.genai.types.GenerateContentConfig` for gemini-2.5-flash-image
are `temperature`, `top_p`, `top_k` and `seed`, which is what this module (and
the UI) exposes instead.
"""

import os
from typing import Optional, Tuple

from google.genai import types

from scoring import get_client

DEFAULT_IMAGE_MODEL = "gemini-2.5-flash-image"

DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 0.95
DEFAULT_TOP_K = 40


def stage_photo(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    top_k: int = DEFAULT_TOP_K,
    seed: Optional[int] = None,
) -> Tuple[bytes, str]:
    """Edit a room photo (add/replace/remove furniture) via a text prompt.

    Returns (image_bytes, mime_type) of the edited image.
    """
    model_name = os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)

    response = get_client().models.generate_content(
        model=model_name,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            seed=seed,
        ),
    )

    for part in response.parts or []:
        if part.inline_data:
            return part.inline_data.data, part.inline_data.mime_type

    finish_reason = response.candidates[0].finish_reason if response.candidates else None
    raise ValueError(
        "Модель не вернула изображение "
        f"(finish_reason={finish_reason}; возможно, запрошенное изменение не применимо к этому фото "
        "или сработал фильтр безопасности)."
    )
