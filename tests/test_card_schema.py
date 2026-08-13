"""Tests for the explicit card/account schema validator."""

import pandas as pd
import pytest

from fraud_detection import validate_card_schema


def _issue_codes(report: dict[str, object]) -> set[str]:
    issues = report["issues"]
    assert isinstance(issues, list)
    return {issue["code"] for issue in issues}


def test_validate_card_schema_accepts_valid_data(valid_card_data: pd.DataFrame) -> None:
    report = validate_card_schema(valid_card_data)

    assert report["is_valid"] is True
    assert report["row_count"] == 2
    assert report["missing_columns"] == []
    assert report["unexpected_columns"] == []
    assert report["issues"] == []


def test_validate_card_schema_reports_missing_column(
    valid_card_data: pd.DataFrame,
) -> None:
    report = validate_card_schema(valid_card_data.drop(columns="card_brand"))

    assert report["is_valid"] is False
    assert report["missing_columns"] == ["card_brand"]
    assert "missing_required_columns" in _issue_codes(report)


def test_validate_card_schema_reports_unexpected_column(
    valid_card_data: pd.DataFrame,
) -> None:
    report = validate_card_schema(valid_card_data.assign(unexpected="value"))

    assert report["is_valid"] is False
    assert report["unexpected_columns"] == ["unexpected"]
    assert "unexpected_columns" in _issue_codes(report)


@pytest.mark.parametrize(
    ("column", "bad_value", "expected_code"),
    [
        ("credit_limit", "not currency", "invalid_currency"),
        ("acct_open_date", "2020-01", "invalid_month_year"),
        ("expires", "13/2030", "invalid_month_year"),
        ("has_chip", "sometimes", "invalid_boolean"),
        ("card_on_dark_web", "unknown", "invalid_boolean"),
        ("num_cards_issued", "many", "invalid_integer"),
    ],
)
def test_validate_card_schema_reports_malformed_values(
    valid_card_data: pd.DataFrame,
    column: str,
    bad_value: str,
    expected_code: str,
) -> None:
    invalid = valid_card_data.copy()
    invalid[column] = invalid[column].astype("object")
    invalid.loc[0, column] = bad_value

    report = validate_card_schema(invalid)

    assert report["is_valid"] is False
    assert expected_code in _issue_codes(report)


def test_validate_card_schema_reports_duplicate_record_ids(
    valid_card_data: pd.DataFrame,
) -> None:
    invalid = valid_card_data.copy()
    invalid["id"] = [1, 1]

    report = validate_card_schema(invalid)

    assert "duplicate_identifier" in _issue_codes(report)


def test_validation_messages_never_contain_cell_values(
    valid_card_data: pd.DataFrame,
) -> None:
    marker = "PRIVATE-MARKER-MUST-NOT-LEAK"
    invalid = valid_card_data.copy()
    invalid.loc[0, "card_number"] = marker
    invalid.loc[0, "cvv"] = None

    report = validate_card_schema(invalid)

    assert marker not in repr(report)


def test_validate_card_schema_requires_dataframe() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        validate_card_schema([])  # type: ignore[arg-type]


def test_validate_card_schema_rejects_header_only_data(
    valid_card_data: pd.DataFrame,
) -> None:
    report = validate_card_schema(valid_card_data.iloc[0:0])

    assert report["is_valid"] is False
    assert "empty_dataset" in _issue_codes(report)
