import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN env variable is not set")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY env variable is not set")
