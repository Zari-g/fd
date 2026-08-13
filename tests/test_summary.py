"""Tests for exploratory summaries."""

import pandas as pd

from fraud_detection import summarize_dataset


def test_summarize_dataset_returns_structured_summary() -> None:
    df = pd.DataFrame(
        {
            "amount": [12.5, None, 12.5],
            "merchant": ["A", "B", "A"],
            "occurred_at": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-03"]
            ),
        }
    )

    result = summarize_dataset(df)

    assert result == {
        "row_count": 3,
        "column_count": 3,
        "columns": ["amount", "merchant", "occurred_at"],
        "numeric_columns": ["amount"],
        "categorical_columns": ["merchant"],
        "datetime_columns": ["occurred_at"],
        "missing_values": {"amount": 1, "merchant": 0, "occurred_at": 0},
        "duplicate_rows": 0,
    }


def test_summarize_dataset_detects_duplicates() -> None:
    df = pd.DataFrame({"amount": [10, 10], "merchant": ["A", "A"]})

    result = summarize_dataset(df)

    assert result["duplicate_rows"] == 1
