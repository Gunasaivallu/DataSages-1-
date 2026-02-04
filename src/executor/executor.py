import json
import pandas as pd
import plotly.express as px


# -----------------------------------------------------
# 🔢 SAFE NUMERIC COERCION
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

        if isinstance(val, str) and val.startswith("[") and val.endswith("]"):
            try:
                val = json.loads(val.replace("'", '"'))
            except Exception:
                pass

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

    original_filtered_df = working_df.copy()

    # =================================================
    # 📊 AGGREGATION
    # =================================================
    metrics = plan.get("metrics", [])
    group_by = plan.get("group_by", [])

    # -----------------------------------------------
    # COUNT ONLY CASE
    # -----------------------------------------------
    if (
        not group_by
        and len(metrics) == 1
        and metrics[0]["operation"] == "count"
    ):
        count_col = metrics[0]["column"]

        if working_df[count_col].dtype != "object":
            result_df = pd.DataFrame({"count": [len(working_df)]})
        else:
            result_df = pd.DataFrame({
                "count": [working_df[count_col].nunique()]
            })

    # -----------------------------------------------
    # GROUP BY SAFE AGGREGATION
    # -----------------------------------------------
    elif group_by:

        agg_map = {}

        for m in metrics:
            col = m["column"]
            op = m["operation"]

            # ❌ NEVER aggregate group_by columns
            if col in group_by:
                continue

            agg_map[col] = op

        if agg_map:
            result_df = (
                working_df
                .groupby(group_by, as_index=False)
                .agg(agg_map)
            )
        else:
            result_df = working_df[group_by].drop_duplicates()

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
    # 🔝 TOP N
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

        if y is None and metrics:
            for m in metrics:
                if m["column"] in result_df.columns:
                    y = m["column"]
                    break

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
