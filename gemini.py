"""
GigaChat Vision integration.
Foto flow: upload file → get file_id → send chat with attachment.
Text flow: send chat directly.
"""
import httpx
import json
import re
import os
import asyncio

GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_BASE_URL = "https://gigachat.devices.sberbank.ru/api/v1"

FOOD_PROMPT = """Ты — эксперт по питанию. Проанализируй фото еды и верни ТОЛЬКО JSON (без markdown, без ```)

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

_access_token = None
_token_expires = 0


async def _get_token() -> str:
    global _access_token, _token_expires
    now = asyncio.get_event_loop().time()
    if _access_token and now < _token_expires:
        return _access_token

    credentials = os.environ["GIGACHAT_CREDENTIALS"]
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.post(
            GIGACHAT_AUTH_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "RqUID": "calorie-bot-001",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"scope": "GIGACHAT_API_PERS"},
        )
        resp.raise_for_status()
    data = resp.json()
    _access_token = data["access_token"]
    _token_expires = now + data.get("expires_at", 1800) / 1000 - 60
    return _access_token


def _parse(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        text = m.group()
    return json.loads(text)


async def _upload_image(image_bytes: bytes, token: str) -> str:
    """Upload image to GigaChat, return file_id."""
    async with httpx.AsyncClient(verify=False, timeout=60) as client:
        resp = await client.post(
            f"{GIGACHAT_BASE_URL}/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("photo.jpg", image_bytes, "image/jpeg")},
            data={"purpose": "general"},
        )
        resp.raise_for_status()
    return resp.json()["id"]


async def analyze_food_photo(image_bytes: bytes) -> dict:
    token = await _get_token()
    file_id = await _upload_image(image_bytes, token)

    payload = {
        "model": "GigaChat-2-Pro",
        "temperature": 0.2,
        "messages": [
            {
                "role": "user",
                "content": FOOD_PROMPT,
                "attachments": [file_id],
            }
        ],
    }

    async with httpx.AsyncClient(verify=False, timeout=60) as client:
        resp = await client.post(
            f"{GIGACHAT_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()

    text = resp.json()["choices"][0]["message"]["content"]
    return _parse(text)


async def analyze_food_text(description: str) -> dict:
    token = await _get_token()

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
        "model": "GigaChat-2-Pro",
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(verify=False, timeout=60) as client:
        resp = await client.post(
            f"{GIGACHAT_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()

    text = resp.json()["choices"][0]["message"]["content"]
    return _parse(text)
