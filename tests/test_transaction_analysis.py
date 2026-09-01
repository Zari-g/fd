"""Tests for aggregate-only summaries and explicit in-store filtering."""

from decimal import Decimal

import pandas as pd

from fraud_detection import (
    filter_in_store_transactions,
    preprocess_transaction_data,
    summarize_transactions,
)


def test_unlabeled_transaction_summary(valid_transaction_data: pd.DataFrame) -> None:
    transactions = preprocess_transaction_data(valid_transaction_data)
    summary = summarize_transactions(transactions)

    assert summary["transaction_count"] == 3
    assert summary["unique_transaction_count"] == 3
    assert summary["unique_card_count"] == 2
    assert summary["unique_merchant_count"] == 2
    assert summary["currency_counts"] == {"CAD": 2, "USD": 1}
    assert summary["channel_counts"] == {"in_store": 2, "online": 1}
    assert summary["label_available"] is False
    assert summary["amount"] == {
        "minimum": Decimal("-2.50"),
        "maximum": Decimal("100"),
        "median": Decimal("10.25"),
        "mean": Decimal("35.91666666666666666666666667"),
        "total": Decimal("107.75"),
    }


def test_labeled_transaction_summary(valid_transaction_data: pd.DataFrame) -> None:
    transactions = preprocess_transaction_data(
        valid_transaction_data.assign(fraud_label=["yes", "no", None])
    )
    summary = summarize_transactions(transactions)
    assert summary["label_available"] is True
    assert summary["labeled_transaction_count"] == 2
    assert summary["fraud_count"] == 1
    assert summary["non_fraud_count"] == 1
    assert summary["unlabeled_count"] == 1
    assert summary["fraud_rate_among_labeled"] == 0.5


def test_summary_contains_no_transaction_records(
    valid_transaction_data: pd.DataFrame,
) -> None:
    marker = "merchant_private_marker"
    data = valid_transaction_data.copy()
    data.loc[0, "merchant_id"] = marker
    summary = summarize_transactions(preprocess_transaction_data(data))
    assert marker not in repr(summary)
    assert "txn_001" not in repr(summary)


def test_in_store_filter_is_explicit_and_immutable(
    valid_transaction_data: pd.DataFrame,
) -> None:
    transactions = preprocess_transaction_data(valid_transaction_data)
    original = transactions.copy(deep=True)
    result = filter_in_store_transactions(transactions)

    assert len(result) == 2
    assert result["channel"].eq("in_store").all()
    assert "txn_002" not in result["transaction_id"].tolist()
    pd.testing.assert_frame_equal(transactions, original)


def test_in_store_filter_does_not_admit_unknown_values() -> None:
    data = pd.DataFrame({"channel": ["in_store", "unknown", "online"]})
    result = filter_in_store_transactions(data)
    assert result["channel"].tolist() == ["in_store"]
