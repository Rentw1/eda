import httpx
import base64
import json
import re
from config import GEMINI_API_KEY

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash-lite:generateContent?key=" + GEMINI_API_KEY
)

SYSTEM_PROMPT = """Ты — эксперт по питанию. Проанализируй фото еды и верни ТОЛЬКО JSON (без markdown, без ```).

Формат ответа:
{
  "name": "название блюда на русском",
  "estimated_grams": 200,
  "kcal_per_100g": 150,
  "protein_per_100g": 10.5,
  "fat_per_100g": 5.2,
  "carbs_per_100g": 20.1,
  "confidence": "high|medium|low",
  "note": "короткая заметка если нужна"
}

Правила:
- estimated_grams — твоя оценка порции на фото
- все нутриенты на 100г продукта
- если на фото несколько блюд — укажи самое калорийное/основное
- confidence: high если блюдо чётко видно, low если сложно определить
"""

async def analyze_food_photo(image_bytes: bytes) -> dict | None:
    """Send photo to Gemini, return parsed nutrition dict or None on error."""
    image_b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GEMINI_URL, json=payload)
        resp.raise_for_status()

    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Strip possible markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    return json.loads(text)

async def analyze_food_text(description: str) -> dict | None:
    """Analyze food by text description (e.g. '200г гречки с курицей')."""
    prompt = f"""Ты — эксперт по питанию. Пользователь описал еду: "{description}"

Верни ТОЛЬКО JSON (без markdown, без ```):
{{
  "name": "название блюда",
  "estimated_grams": 200,
  "kcal_per_100g": 150,
  "protein_per_100g": 10.5,
  "fat_per_100g": 5.2,
  "carbs_per_100g": 20.1,
  "confidence": "high|medium|low",
  "note": ""
}}

Если пользователь указал граммы — используй их в estimated_grams."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512}
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GEMINI_URL, json=payload)
        resp.raise_for_status()

    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    return json.loads(text)
