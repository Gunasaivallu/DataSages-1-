import pandas as pd

def analyze_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns dataset-level information as a table.
    """

    info = []

    for col in df.columns:
        info.append({
            "Column": col,
            "Data Type": str(df[col].dtype),
            "Non-Null Count": df[col].notnull().sum(),
            "Missing Values": df[col].isnull().sum(),
            "Unique Values": df[col].nunique()
        })

    return pd.DataFrame(info)
