"""Tests for transaction schema and domain validation."""

import pandas as pd
import pytest

from fraud_detection import validate_transaction_schema


def _codes(report: dict[str, object]) -> set[str]:
    issues = report["issues"]
    assert isinstance(issues, list)
    return {issue["code"] for issue in issues}


def test_valid_required_schema_and_optional_fields_absent(
    valid_transaction_data: pd.DataFrame,
) -> None:
    report = validate_transaction_schema(valid_transaction_data)
    assert report["is_valid"] is True
    assert report["missing_columns"] == []
    assert report["unexpected_columns"] == []


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda df: df.drop(columns="amount"), "missing_required_columns"),
        (lambda df: df.assign(extra="x"), "unexpected_columns"),
        (lambda df: df.assign(card_id=[1, "", 1]), "empty_required_values"),
        (
            lambda df: df.assign(transaction_id=["txn_001", "txn_001", "txn_003"]),
            "duplicate_transaction_id",
        ),
        (lambda df: df.assign(card_id=[1, "bad", 1]), "invalid_card_id"),
        (
            lambda df: df.assign(transaction_timestamp=["bad", "2026-01-01", "2026-01-02"]),
            "invalid_timestamp",
        ),
        (lambda df: df.assign(amount=["10.001", "NaN", "2"]), "invalid_amount"),
        (lambda df: df.assign(currency=["CAD", "CA", "USD"]), "invalid_currency_code"),
        (lambda df: df.assign(channel=["POS", "unknown", "online"]), "invalid_channel"),
        (lambda df: df.assign(fraud_label=["Yes", "maybe", None]), "invalid_fraud_label"),
        (
            lambda df: df.assign(fraud_confirmed_at=["bad", None, None]),
            "invalid_timestamp",
        ),
    ],
)
def test_schema_reports_transaction_issues(
    valid_transaction_data: pd.DataFrame,
    change: object,
    code: str,
) -> None:
    report = validate_transaction_schema(change(valid_transaction_data))  # type: ignore[operator]
    assert report["is_valid"] is False
    assert code in _codes(report)


def test_schema_detects_confirmation_before_transaction(
    valid_transaction_data: pd.DataFrame,
) -> None:
    data = valid_transaction_data.assign(
        fraud_label=[True, False, None],
        fraud_confirmed_at=["2026-08-01T13:00:00-04:00", None, None],
    )
    report = validate_transaction_schema(data)
    assert "fraud_confirmation_before_transaction" in _codes(report)


def test_labels_without_provenance_are_valid_but_warned(
    valid_transaction_data: pd.DataFrame,
) -> None:
    report = validate_transaction_schema(
        valid_transaction_data.assign(fraud_label=[True, False, None])
    )
    assert report["is_valid"] is True
    assert "missing_fraud_label_source" in _codes(report)
    assert "missing_fraud_confirmation_time" in _codes(report)


def test_schema_report_does_not_leak_values(valid_transaction_data: pd.DataFrame) -> None:
    marker = "PRIVATE-MARKER-MUST-NOT-LEAK"
    data = valid_transaction_data.assign(channel=[marker, "online", "mobile"])
    assert marker not in repr(validate_transaction_schema(data))


def test_transaction_schema_requires_dataframe() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        validate_transaction_schema([])  # type: ignore[arg-type]
