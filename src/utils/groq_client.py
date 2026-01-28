from groq import Groq
from src.config import GROQ_API_KEY

def get_groq_client():
    return Groq(api_key=GROQ_API_KEY)
