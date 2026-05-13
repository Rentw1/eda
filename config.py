import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN env variable is not set")
if not GIGACHAT_CREDENTIALS:
    raise ValueError("GIGACHAT_CREDENTIALS env variable is not set")
