import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN env variable is not set")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN env variable is not set")
