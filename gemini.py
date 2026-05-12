import httpx
import base64
import json
import re
import os

HF_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-VL-3B-Instruct/v1/chat/completions"

FOOD_PROMPT = """Analyze this food photo and return ONLY JSON (no markdown, no ```).

Format:
{
  "name": "dish name in Russian",
  "estimated_grams": 200,
  "kcal_per_100g": 150,
  "protein_per_100g": 10.5,
  "fat_per_100g": 5.2,
  "carbs_per_100g": 20.1,
  "confidence": "high",
  "note": ""
}

Rules:
- estimated_grams is your estimate of the portion in the photo
- all nutrients per 100g
- confidence: high if food is clearly visible, low if hard to determine"""


def _headers():
    token = os.environ["HF_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _parse(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # find JSON object in text
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        text = m.group()
    return json.loads(text)


async def analyze_food_photo(image_bytes: bytes) -> dict:
    image_b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "model": "Qwen/Qwen2.5-VL-3B-Instruct",
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
        resp = await client.post(HF_URL, json=payload, headers=_headers())
        resp.raise_for_status()

    text = resp.json()["choices"][0]["message"]["content"]
    return _parse(text)


async def analyze_food_text(description: str) -> dict:
    prompt = f"""User described food: "{description}"

Return ONLY JSON (no markdown):
{{
  "name": "dish name in Russian",
  "estimated_grams": 200,
  "kcal_per_100g": 150,
  "protein_per_100g": 10.5,
  "fat_per_100g": 5.2,
  "carbs_per_100g": 20.1,
  "confidence": "high",
  "note": ""
}}

If user specified grams, use them in estimated_grams."""

    payload = {
        "model": "Qwen/Qwen2.5-VL-3B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(HF_URL, json=payload, headers=_headers())
        resp.raise_for_status()

    text = resp.json()["choices"][0]["message"]["content"]
    return _parse(text)
