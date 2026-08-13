"""Reusable dataset summary functions."""

from typing import Any

import pandas as pd

from fraud_detection.data.validation import validate_dataset


def summarize_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """Return a concise exploratory summary of a DataFrame.

    Non-numeric, non-datetime columns are reported as categorical candidates;
    callers can refine these classifications when a domain schema is added.
    """
    validation = validate_dataset(df)
    numeric_columns = list(df.select_dtypes(include="number").columns)
    datetime_columns = list(
        df.select_dtypes(include=["datetime", "datetimetz"]).columns
    )
    categorical_columns = [
        column
        for column in df.columns
        if column not in numeric_columns and column not in datetime_columns
    ]

    return {
        "row_count": validation["shape"][0],
        "column_count": validation["shape"][1],
        "columns": list(df.columns),
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "datetime_columns": datetime_columns,
        "missing_values": validation["missing_values"],
        "duplicate_rows": validation["duplicate_rows"],
    }

