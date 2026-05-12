import httpx
import base64
import json
import re
import os

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "qwen/qwen2.5-vl-3b-instruct:free"

FOOD_PROMPT = """Ты — эксперт по питанию. Проанализируй фото еды и верни ТОЛЬКО JSON (без markdown, без ```).

Формат:
{
  "name": "название блюда на русском",
  "estimated_grams": 200,
  "kcal_per_100g": 150,
  "protein_per_100g": 10.5,
  "fat_per_100g": 5.2,
  "carbs_per_100g": 20.1,
  "confidence": "high",
  "note": ""
}

Правила:
- estimated_grams — твоя оценка порции на фото
- все нутриенты на 100г
- confidence: high если блюдо чётко видно, low если сложно"""


def _headers():
    key = os.environ["OPENROUTER_API_KEY"]
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://calorie-bot",
    }


def _parse(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


async def analyze_food_photo(image_bytes: bytes) -> dict:
    image_b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": FOOD_PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}"
                    }}
                ]
            }
        ],
        "max_tokens": 512,
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(OPENROUTER_URL, json=payload, headers=_headers())
        resp.raise_for_status()

    text = resp.json()["choices"][0]["message"]["content"]
    return _parse(text)


async def analyze_food_text(description: str) -> dict:
    prompt = f"""Ты — эксперт по питанию. Пользователь описал еду: "{description}"

Верни ТОЛЬКО JSON (без markdown, без ```):
{{
  "name": "название блюда",
  "estimated_grams": 200,
  "kcal_per_100g": 150,
  "protein_per_100g": 10.5,
  "fat_per_100g": 5.2,
  "carbs_per_100g": 20.1,
  "confidence": "high",
  "note": ""
}}

Если пользователь указал граммы — используй их в estimated_grams."""

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(OPENROUTER_URL, json=payload, headers=_headers())
        resp.raise_for_status()

    text = resp.json()["choices"][0]["message"]["content"]
    return _parse(text)
