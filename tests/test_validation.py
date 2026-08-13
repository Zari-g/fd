"""Tests for generic dataset validation."""

import pandas as pd
import pytest

from fraud_detection import validate_dataset


def test_validate_dataset_reports_quality_issues() -> None:
    df = pd.DataFrame(
        {
            "card_id": [1, 1, 2, 3],
            "amount": [10.0, 10.0, None, 10.0],
            "empty": [None, None, None, None],
        }
    )

    result = validate_dataset(df)

    assert result["shape"] == (4, 3)
    assert result["is_empty"] is False
    assert result["missing_values"] == {"card_id": 0, "amount": 1, "empty": 4}
    assert result["duplicate_rows"] == 1
    assert result["completely_empty_columns"] == ["empty"]
    assert result["column_dtypes"]["card_id"] == "int64"


def test_validate_dataset_reports_empty_dataframe() -> None:
    df = pd.DataFrame(columns=["card_id"])

    result = validate_dataset(df)

    assert result["shape"] == (0, 1)
    assert result["is_empty"] is True
    assert result["completely_empty_columns"] == ["card_id"]


def test_validate_dataset_requires_dataframe() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        validate_dataset([])  # type: ignore[arg-type]
