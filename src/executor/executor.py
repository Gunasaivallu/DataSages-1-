import json
import pandas as pd
import plotly.express as px


# -----------------------------------------------------
# 🔢 SAFE NUMERIC COERCION (handles %, strings, spaces)
# -----------------------------------------------------
def _coerce_numeric(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .pipe(pd.to_numeric, errors="coerce")
    )


# -----------------------------------------------------
# ⚙️ MAIN EXECUTION ENGINE
# -----------------------------------------------------
def execute_plan(df, plan):
    working_df = df.copy()
    original_filtered_df = None

    # =================================================
    # 🔎 FILTERS
    # =================================================
    for f in plan.get("filters", []):
        col = f.get("column")
        op = f.get("operator")
        val = f.get("value")

        # Fix stringified lists defensively
        if isinstance(val, str) and val.startswith("[") and val.endswith("]"):
            try:
                val = json.loads(val.replace("'", '"'))
            except Exception:
                pass

        # 🔥 AUTO FIX: numeric comparison on string columns
        if op in {">", "<", ">=", "<="}:
            working_df[col] = _coerce_numeric(working_df[col])
            val = float(val)

        if op == "==":
            working_df = working_df[working_df[col] == val]

        elif op == "!=":
            working_df = working_df[working_df[col] != val]

        elif op == ">":
            working_df = working_df[working_df[col] > val]

        elif op == "<":
            working_df = working_df[working_df[col] < val]

        elif op == ">=":
            working_df = working_df[working_df[col] >= val]

        elif op == "<=":
            working_df = working_df[working_df[col] <= val]

        elif op == "in":
            if not isinstance(val, list):
                val = [val]
            working_df = working_df[working_df[col].isin(val)]

    # Save filtered data (for explainer / dual intent)
    original_filtered_df = working_df.copy()

    # =================================================
    # 📊 AGGREGATION
    # =================================================
    metrics = plan.get("metrics", [])
    group_by = plan.get("group_by", [])

    # 🔥 CRITICAL FIX: "HOW MANY X" → DISTINCT COUNT
    # --------------------------------------------------
# 🔥 FIX: "HOW MANY RECORDS / STUDENTS" → ROW COUNT
# --------------------------------------------------
    if (
        not group_by
        and len(metrics) == 1
        and metrics[0]["operation"] == "count"
    ):
        count_col = metrics[0]["column"]

        # If column is NOT an identifier, count rows instead
        if working_df[count_col].dtype != "object":
            result_df = pd.DataFrame({
                "count": [len(working_df)]
            })
        else:
            # Identifier-like column (names, IDs)
            result_df = pd.DataFrame({
                "count": [working_df[count_col].nunique()]
            })


    elif group_by:
        agg_map = {}
        for m in metrics:
            agg_map[m["column"]] = m["operation"]

        if agg_map:
            result_df = (
                working_df
                .groupby(group_by)
                .agg(agg_map)
                .reset_index()
            )
        else:
            result_df = working_df.drop_duplicates(subset=group_by)

    else:
        result_df = working_df.copy()

    # =================================================
    # 🔀 SORTING
    # =================================================
    sort_cfg = plan.get("sort")
    if sort_cfg and sort_cfg.get("by"):
        by_col = sort_cfg["by"]
        if by_col in result_df.columns:
            result_df = result_df.sort_values(
                by=by_col,
                ascending=sort_cfg.get("order", "asc") == "asc"
            )

    # =================================================
    # 🔝 TOP-N (INTENT AWARE)
    # =================================================
    viz = plan.get("visualization", {})
    user_intent = plan.get("user_intent", {})
    top_n = viz.get("top_n")

    if user_intent.get("focus") != "both" and top_n:
        result_df = result_df.head(int(top_n))

    # =================================================
    # 📈 VISUALIZATION
    # =================================================
    fig = None
    if viz and viz.get("type"):
        viz_type = viz.get("type")
        x = viz.get("x")
        y = viz.get("y")

        # Auto-detect y if missing
        if y is None and metrics:
            for m in metrics:
                if m["column"] in result_df.columns:
                    y = m["column"]
                    break

        # Validate y-axis
        if y and y not in result_df.columns:
            raise ValueError(
                f"Invalid y-axis '{y}'. "
                f"Available columns: {list(result_df.columns)}"
            )

        if viz_type == "bar" and x and y:
            fig = px.bar(result_df, x=x, y=y, color=viz.get("color"))

        elif viz_type == "line" and x and y:
            fig = px.line(result_df, x=x, y=y, color=viz.get("color"))

        elif viz_type == "scatter" and x and y:
            fig = px.scatter(result_df, x=x, y=y, color=viz.get("color"))

        elif viz_type == "histogram" and x:
            fig = px.histogram(result_df, x=x, color=viz.get("color"))

    return result_df, fig, original_filtered_df
