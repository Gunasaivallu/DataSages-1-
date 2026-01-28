import streamlit as st
import pandas as pd
import json
import os
import numpy as np
from groq import Groq
from config import MODEL_NAME
from dotenv import load_dotenv

load_dotenv()

# ==================================================
# 🔐 GROQ CLIENT
# ==================================================
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ GROQ_API_KEY not found.")
    return Groq(api_key=api_key)

# ==================================================
# 🛡 JSON SAFETY
# ==================================================
def make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif pd.isna(obj):
        return None
    else:
        return obj

# ==================================================
# 🔎 RESULT COMPRESSION (INTENT-AWARE)
# ==================================================
def compress_result_for_llm(result_df: pd.DataFrame, plan: dict):
    intent = plan.get("user_intent", {})
    focus = intent.get("focus")

    # Highest / Lowest
    if focus in ["highest", "lowest"]:
        return result_df.head(1).to_dict(orient="records")

    # Both
    if focus == "both":
        return (
            pd.concat([result_df.head(1), result_df.tail(1)])
            .drop_duplicates()
            .to_dict(orient="records")
        )

    # List intent → return names
    if focus == "list":
        if not result_df.empty:
            col = result_df.columns[0]
            return result_df[col].astype(str).tolist()

    # Count / aggregation
    if result_df.shape[0] == 1:
        return result_df.to_dict(orient="records")

    # Safe default
    return result_df.head(10).to_dict(orient="records")

# ==================================================
# 🧠 EXPLAINER AGENT (IMPROVED)
# ==================================================
class ExplainerAgent:
    def __init__(self):
        self.client = get_groq_client()
        self.model = MODEL_NAME

        self.system_prompt = """
You are a senior data analyst explaining insights to business stakeholders.

Rules:
- Answer ONLY using the provided results
- Do NOT analyze raw datasets
- Do NOT invent trends or causes
- Use clear, non-technical language
- Be concise and practical
"""

    # --------------------------------------------------
    # 💡 MAIN EXPLAIN METHOD
    # --------------------------------------------------
    def explain(self, question: str, result_df: pd.DataFrame, plan: dict) -> str:

        if result_df is None or result_df.empty:
            return "No meaningful results were found for this question."

        compressed_result = compress_result_for_llm(result_df, plan)

        payload = {
            "question": question,
            "analysis_plan": plan,
            "results": compressed_result,
            "total_rows": len(result_df)
        }

        payload = make_json_safe(payload)

        user_prompt = f"""
User question:
{question}

Analysis summary:
{json.dumps(payload, indent=2)}

Instructions:
- Start with a direct 1–2 sentence answer to the question
- Then give 3–5 bullet points with key insights
- Use exact numbers when available
- If this is a list question, clearly list the entities
- Avoid technical or database terms
- End with a brief takeaway if appropriate

Format EXACTLY like this:

Direct Answer and key insights:
<large answer>
• point 1
• point 2
• point 3
"""

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content.strip()

    # --------------------------------------------------
    # 📊 DATASET OVERVIEW (ONLY IF ASKED)
    # --------------------------------------------------
    def explain_dataset(self, df: pd.DataFrame) -> str:
        overview = {"columns": list(df.columns)}

        user_prompt = f"""
Briefly describe what this dataset contains.

{json.dumps(overview, indent=2)}

Rules:
- Keep it short
- Do NOT infer statistics
"""

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content.strip()
