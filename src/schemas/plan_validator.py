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
    # 🔥 METRICS (DEFENSIVE + INTENT AWARE)
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

    # Replace metrics with cleaned version
    plan["metrics"] = cleaned_metrics

    # Distribution & correlation MUST NOT have metrics
    if analysis_type in {"distribution", "correlation"} and plan["metrics"]:
        raise ValueError(
            f"{analysis_type} analysis must not contain metrics"
        )

    # --------------------------------------------------
    # VISUALIZATION - PROPERLY HANDLE NULL VALUES
    # --------------------------------------------------
    viz = plan["visualization"]
    if not viz:
        return True

    # 🔥 FIX: Convert string "null"/"NULL" to actual None
    for key in ["x", "y", "color", "top_n"]:
        if key in viz:
            if viz[key] in ("null", "NULL"):
                viz[key] = None

    if viz["type"] not in ALLOWED_VIZ_TYPES:
        raise ValueError(f"Invalid visualization type: {viz['type']}")

    # --------------------------------------------------
    # TYPE-SPECIFIC VALIDATION
    # --------------------------------------------------
    
    # Histogram rules
    if viz["type"] == "histogram":
        if viz.get("y") is not None:
            raise ValueError("Histogram must not have y-axis")
        if viz.get("x") is None:
            raise ValueError("Histogram must have x-axis specified")

    # Correlation rules
    if analysis_type == "correlation":
        if viz["type"] != "scatter":
            raise ValueError("Correlation requires scatter plot")
        if viz.get("x") is None or viz.get("y") is None:
            raise ValueError("Correlation scatter plot must have both x and y axes")

    # --------------------------------------------------
    # VALIDATE X/Y AXES (ONLY IF NOT NULL)
    # --------------------------------------------------
    
    # Only validate x if it's not None
    if viz.get("x") is not None and viz["x"] not in df_columns:
        raise ValueError(f"Invalid x-axis: {viz['x']}")

    # Only validate y if it's not None AND not a valid case for null
    if viz.get("y") is not None:
        if viz["y"] not in df_columns:
            raise ValueError(f"Invalid y-axis: {viz['y']}")

    # --------------------------------------------------
    # TOP N VALIDATION
    # --------------------------------------------------
    if viz.get("top_n") is not None:
        if not isinstance(viz["top_n"], int) or viz["top_n"] <= 0:
            raise ValueError("top_n must be a positive integer")

    return True