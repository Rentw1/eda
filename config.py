import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN env variable is not set")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY env variable is not set")
