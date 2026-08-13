"""Generic dataset validation utilities."""

from typing import Any

import pandas as pd


def validate_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """Return basic structural and data-quality checks for a DataFrame.

    The function reports observations rather than enforcing a domain-specific
    schema, making it suitable for datasets added in future iterations.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    return {
        "shape": df.shape,
        "is_empty": df.empty,
        "missing_values": {
            column: int(count) for column, count in df.isna().sum().items()
        },
        "duplicate_rows": int(df.duplicated().sum()),
        "column_dtypes": {
            column: str(dtype) for column, dtype in df.dtypes.items()
        },
        "completely_empty_columns": [
            column for column in df.columns if df[column].isna().all()
        ],
    }

