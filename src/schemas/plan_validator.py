# schemas/plan_validator.py

ALLOWED_ANALYSIS_TYPES = {
    "comparison",
    "trend",
    "aggregation",
    "correlation",
    "distribution"
}

ALLOWED_OPERATORS = {"==", "!=", ">", "<", ">=", "<=", "in"}
ALLOWED_METRICS = {"sum", "mean", "count", "min", "max", "median", "std"}
ALLOWED_VIZ_TYPES = {"bar", "line", "scatter", "histogram"}

# ⛔ Visualization keywords that MUST NOT appear in metrics
INVALID_METRIC_OPERATIONS = {"bar", "line", "scatter", "histogram"}


def validate_plan(plan: dict, df_columns: list):

    if not isinstance(plan, dict):
        raise ValueError("Plan must be a dictionary")

    # --------------------------------------------------
    # REQUIRED KEYS
    # --------------------------------------------------
    required_keys = [
        "analysis_type",
        "filters",
        "group_by",
        "metrics",
        "sort",
        "visualization"
    ]

    for key in required_keys:
        if key not in plan:
            raise ValueError(f"Missing key: {key}")

    analysis_type = plan["analysis_type"]

    if analysis_type not in ALLOWED_ANALYSIS_TYPES:
        raise ValueError(f"Invalid analysis_type: {analysis_type}")

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------
    for f in plan["filters"]:
        if f["column"] not in df_columns:
            raise ValueError(f"Invalid filter column: {f['column']}")
        if f["operator"] not in ALLOWED_OPERATORS:
            raise ValueError(f"Invalid operator: {f['operator']}")
        if f["operator"] == "in" and not isinstance(f["value"], list):
            raise ValueError("Operator 'in' requires a list value")

    # --------------------------------------------------
    # GROUP BY
    # --------------------------------------------------
    for col in plan["group_by"]:
        if col not in df_columns:
            raise ValueError(f"Invalid group_by column: {col}")

    # --------------------------------------------------
    # 🔥 METRICS CLEANING
    # --------------------------------------------------
    cleaned_metrics = []

    for m in plan["metrics"]:
        op = m.get("operation")

        # 🚫 Drop visualization operations silently
        if op in INVALID_METRIC_OPERATIONS:
            continue

        if op not in ALLOWED_METRICS:
            raise ValueError(
                f"Invalid metric operation '{op}'. "
                "Only statistical operations are allowed."
            )

        if m["column"] not in df_columns:
            raise ValueError(f"Invalid metric column: {m['column']}")

        cleaned_metrics.append(m)

    plan["metrics"] = cleaned_metrics

    # Distribution & correlation MUST NOT have metrics
    if analysis_type in {"distribution", "correlation"} and plan["metrics"]:
        raise ValueError(
            f"{analysis_type} analysis must not contain metrics"
        )

    # --------------------------------------------------
    # VISUALIZATION
    # --------------------------------------------------
    viz = plan["visualization"]
    if not viz:
        return True

    # convert string null → None
    for key in ["x", "y", "color", "top_n"]:
        if key in viz and viz[key] in ("null", "NULL"):
            viz[key] = None

    if viz["type"] not in ALLOWED_VIZ_TYPES:
        raise ValueError(f"Invalid visualization type: {viz['type']}")

    # --------------------------------------------------
    # 🔥 AUTO-FIX: metric accidentally placed in y-axis
    # --------------------------------------------------
    if viz.get("y") in ALLOWED_METRICS:
        # move metric into metrics list
        if plan["group_by"]:
            target_col = plan["group_by"][0]
        else:
            target_col = df_columns[0]

        plan["metrics"].append({
            "operation": viz["y"],
            "column": target_col
        })

        viz["y"] = target_col

    # --------------------------------------------------
    # TYPE RULES
    # --------------------------------------------------
    if viz["type"] == "histogram":
        if viz.get("y") is not None:
            raise ValueError("Histogram must not have y-axis")
        if viz.get("x") is None:
            raise ValueError("Histogram must have x-axis specified")

    if analysis_type == "correlation":
        if viz["type"] != "scatter":
            raise ValueError("Correlation requires scatter plot")
        if viz.get("x") is None or viz.get("y") is None:
            raise ValueError("Correlation scatter plot must have both x and y axes")

    # --------------------------------------------------
    # AXIS VALIDATION
    # --------------------------------------------------
    if viz.get("x") is not None and viz["x"] not in df_columns:
        raise ValueError(f"Invalid x-axis: {viz['x']}")

    if viz.get("y") is not None and viz["y"] not in df_columns:
        raise ValueError(f"Invalid y-axis: {viz['y']}")

    # --------------------------------------------------
    # TOP N
    # --------------------------------------------------
    if viz.get("top_n") is not None:
        if not isinstance(viz["top_n"], int) or viz["top_n"] <= 0:
            raise ValueError("top_n must be a positive integer")

    return True
