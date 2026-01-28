from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.1-8b-instant"

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in .env")
