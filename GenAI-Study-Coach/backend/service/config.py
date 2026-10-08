import os
from dotenv import load_dotenv

load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID       = os.getenv("MODEL_ID", "gemini-1.5-flash")

print(f"[CONFIG] Using Model: {MODEL_ID}")
print(f"[CONFIG] Gemini API Key loaded: {'Yes' if GEMINI_API_KEY else 'NO - CHECK .env'}")
