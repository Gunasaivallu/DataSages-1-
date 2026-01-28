import json
import os
import re
from groq import Groq
from dotenv import load_dotenv
from config import MODEL_NAME

load_dotenv()


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ GROQ_API_KEY not found.")
    return Groq(api_key=api_key)


class PlannerAgent:
    def __init__(self):
        self.client = get_groq_client()
        self.model = MODEL_NAME

        self.system_prompt = """
You are a Data Analysis Planner Agent.

Convert a user question into STRICTLY VALID JSON
that can be executed by a Pandas-based analysis engine.

ABSOLUTE RULES:
1. Output ONLY valid JSON (no markdown, no explanation).
2. Use ONLY the provided column names.
3. JSON arrays must NOT use numeric keys.
4. Use JSON null (lowercase), NEVER NULL or None.
5. Operator "in" MUST always have a LIST value.
6. Do NOT stringify lists.
7. Aggregated column names remain UNCHANGED.
8. COUNT is allowed on ANY column.
9. Visualization types (bar, line, scatter, histogram)
   MUST NEVER appear in metrics.operation.

CRITICAL INTENT DETECTION:
- "highest/maximum/top/largest" → sort.order = "desc"
- "lowest/minimum/bottom/smallest" → sort.order = "asc"
- If user asks for BOTH highest AND lowest → create TWO separate requests in your mind, but return plan for BOTH
- When "lowest" is detected:
  * set sort.order = "asc"
  * set visualization.top_n appropriately (default 1 if not specified)
  * ensure sort.by targets the correct metric column

ANALYSIS TYPE RULES:

COMPARISON:
- Pattern 1: Compare multiple METRICS by category
  * "compare sales and profit by country"
  * group_by: ["COUNTRY"], metrics: [sales, profit]
  * No filters needed
  
- Pattern 2: Compare specific VALUES within a category
  * "compare sales in USA and UK"
  * filters: [{"column": "COUNTRY", "operator": "in", "value": ["USA", "UK"]}]
  * group_by: ["COUNTRY"]
  * metrics: [{"column": "SALES", "operation": "sum"}]
  * IMPORTANT: Use "in" operator with list of values
  
- visualization.x = category column
- visualization.type = "bar" (default)

TREND:
- Analyze changes over time
- group_by must include a time column (DATE, MONTH, YEAR)
- visualization.type = "line"
- Example: "sales trend over time"
  → group_by: ["DATE"], metrics: [{"column": "SALES", "operation": "sum"}], viz.type: "line"

AGGREGATION:
- Calculate summary statistics
- When "by category": use group_by, set viz.x to category
- When "for specific value": use filters, NO group_by
- DO NOT filter and group_by the same column!
- Examples:
  * "average sales by country" → filters: [], group_by: ["COUNTRY"], viz.x: "COUNTRY"
  * "total sales for USA" → filters: [{"column": "COUNTRY", "value": "USA"}], group_by: []
  * "mean profit by region for USA" → filters: [{"column": "COUNTRY", "value": "USA"}], group_by: ["REGION"]

RANKING (TOP N / BOTTOM N):
- "which country has highest population" → top_n: 1, sort.order: "desc"
- "which country has lowest population" → top_n: 1, sort.order: "asc"
- "top 5 countries by sales" → top_n: 5, sort.order: "desc"
- "bottom 3 regions by profit" → top_n: 3, sort.order: "asc"
- CRITICAL: For questions asking "highest AND lowest" simultaneously:
  * Focus on the PRIMARY intent (usually what comes first in question)
  * Example: "which country has highest population and lowest population"
    → Create plan that can show BOTH by setting appropriate top_n and ensuring full result is available

CORRELATION:
- Relationship between two numeric columns
- analysis_type = "correlation"
- metrics = []
- group_by = []
- visualization.type = "scatter"
- visualization.x = first numeric column
- visualization.y = second numeric column
- Example: "correlation between sales and profit"
  → viz: {type: "scatter", x: "SALES", y: "PROFIT"}

DISTRIBUTION:
- Frequency distribution of a single column
- analysis_type = "distribution"
- metrics = []
- group_by = []
- visualization.type = "histogram"
- visualization.x = column to analyze
- visualization.y = null
- Example: "distribution of sales"
  → viz: {type: "histogram", x: "SALES", y: null}

CRITICAL:
- NEVER use placeholder values like "string", "number", "value" in filters
- Use actual values from the question or leave filters empty []
- Column names in sort.by must match the actual column name (not aggregated name)
- For "both highest and lowest" queries, ensure the plan allows showing both extremes

JSON SCHEMA:
{
  "analysis_type": "comparison | trend | aggregation | correlation | distribution",
  "filters": [
    {
      "column": "string",
      "operator": "== | != | > | < | >= | <= | in",
      "value": "string | number | [string | number]"
    }
  ],
  "group_by": ["string"],
  "metrics": [
    {
      "column": "string",
      "operation": "sum | mean | count | min | max | median | std"
    }
  ],
  "sort": {
    "by": "string",
    "order": "asc | desc"
  },
  "visualization": {
    "type": "bar | line | scatter | histogram",
    "x": "string | null",
    "y": "string | null",
    "color": "string | null",
    "top_n": "number | null"
  },
  "user_intent": {
    "show_highest": "boolean",
    "show_lowest": "boolean",
    "focus": "highest | lowest | both"
  }
}

Validate internally before output.
"""

    def _detect_dual_intent(self, question: str) -> dict:
        """
        Detect if user wants BOTH highest and lowest values.
        """
        q_lower = question.lower()
        
        highest_keywords = ["highest", "maximum", "top", "largest", "most"]
        lowest_keywords = ["lowest", "minimum", "bottom", "smallest", "least"]
        
        has_highest = any(kw in q_lower for kw in highest_keywords)
        has_lowest = any(kw in q_lower for kw in lowest_keywords)
        
        if has_highest and has_lowest:
            return {"show_highest": True, "show_lowest": True, "focus": "both"}
        elif has_highest:
            return {"show_highest": True, "show_lowest": False, "focus": "highest"}
        elif has_lowest:
            return {"show_highest": False, "show_lowest": True, "focus": "lowest"}
        else:
            return {"show_highest": False, "show_lowest": False, "focus": "general"}

    def _sanitize_plan(self, plan: dict, question: str) -> dict:
        """
        Apply universal fixes for ALL analysis types.
        Enhanced with intent detection.
        """
        analysis_type = plan.get("analysis_type")
        
        # Add user intent detection
        intent = self._detect_dual_intent(question)
        plan["user_intent"] = intent

        # Remove visualization words from metrics (ALL TYPES)
        invalid_metric_ops = {"bar", "line", "scatter", "histogram"}
        if plan.get("metrics"):
            plan["metrics"] = [
                m for m in plan["metrics"]
                if m.get("operation") not in invalid_metric_ops
            ]

        # REMOVE PLACEHOLDER FILTER VALUES (ALL TYPES)
        if plan.get("filters"):
            valid_filters = []
            for f in plan["filters"]:
                val = f.get("value")
                if val not in ["string", "number", "value", "list"]:
                    valid_filters.append(f)
            plan["filters"] = valid_filters

        # TYPE-SPECIFIC FIXES
        if analysis_type == "distribution":
            plan["metrics"] = []
            plan["group_by"] = []
            if plan.get("visualization"):
                plan["visualization"]["type"] = "histogram"
                plan["visualization"]["y"] = None

        elif analysis_type == "correlation":
            plan["metrics"] = []
            plan["group_by"] = []
            if plan.get("visualization"):
                plan["visualization"]["type"] = "scatter"

        elif analysis_type == "aggregation":
            if plan.get("filters") and plan.get("group_by"):
                filter_cols = {f.get("column") for f in plan["filters"]}
                group_cols = set(plan["group_by"])
                
                if filter_cols & group_cols:
                    plan["filters"] = [
                        f for f in plan["filters"] 
                        if f.get("column") not in group_cols
                    ]

            if plan.get("group_by") and plan.get("visualization"):
                if plan["visualization"].get("x") is None:
                    plan["visualization"]["x"] = plan["group_by"][0]
            
            # ENHANCED: Handle "both highest and lowest" intent
            if intent["focus"] == "both":
                # Don't limit top_n for dual intent queries
                if plan.get("visualization") and plan["visualization"].get("top_n"):
                    # Remove top_n restriction for dual intent
                    plan["visualization"]["top_n"] = None

        elif analysis_type == "comparison":
            if plan.get("group_by") and plan.get("visualization"):
                if plan["visualization"].get("x") is None:
                    plan["visualization"]["x"] = plan["group_by"][0]
            
            if plan.get("filters"):
                for f in plan["filters"]:
                    if f.get("column") in plan.get("group_by", []):
                        if f.get("operator") == "==" and isinstance(f.get("value"), list):
                            f["operator"] = "in"

        elif analysis_type == "trend":
            if plan.get("visualization"):
                if plan["visualization"].get("type") != "line":
                    plan["visualization"]["type"] = "line"
                if plan.get("group_by") and plan["visualization"].get("x") is None:
                    plan["visualization"]["x"] = plan["group_by"][0]

        return plan

    def generate_plan(self, columns, question):
        user_prompt = f"""
Columns: {columns}
Question: {question}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response.choices[0].message.content
        content = re.sub(r"```json|```", "", content).strip()
        content = content.replace("NULL", "null")

        plan = json.loads(content)

        # APPLY UNIVERSAL SANITIZATION WITH INTENT DETECTION
        plan = self._sanitize_plan(plan, question)

        return plan