"""Tests for deterministic transaction normalization."""

from decimal import Decimal

import pandas as pd
import pytest

from fraud_detection import preprocess_transaction_data
from fraud_detection.preprocessing import TransactionDataValidationError


def test_preprocessing_normalizes_identifiers_money_currency_and_channel(
    valid_transaction_data: pd.DataFrame,
) -> None:
    result = preprocess_transaction_data(valid_transaction_data)

    assert result["transaction_id"].tolist() == ["txn_001", "txn_002", "txn_003"]
    assert str(result["transaction_id"].dtype) == "string"
    assert str(result["card_id"].dtype) == "Int64"
    assert result["merchant_id"].tolist()[0] == "merchant_001"
    assert result["amount"].tolist() == [
        Decimal("10.25"),
        Decimal("-2.50"),
        Decimal("100"),
    ]
    assert result["currency"].tolist() == ["CAD", "USD", "CAD"]
    assert result["channel"].tolist() == ["in_store", "online", "in_store"]


def test_aware_timestamps_are_normalized_to_utc(
    valid_transaction_data: pd.DataFrame,
) -> None:
    result = preprocess_transaction_data(valid_transaction_data)
    assert str(result["transaction_timestamp"].dtype) == "datetime64[ns, UTC]"
    assert result.loc[0, "transaction_timestamp"] == pd.Timestamp(
        "2026-08-01T18:21:13Z"
    )


def test_naive_timestamp_requires_explicit_timezone(
    valid_transaction_data: pd.DataFrame,
) -> None:
    data = valid_transaction_data.assign(
        transaction_timestamp=["2026-08-01 14:00:00"] * 3
    )
    with pytest.raises(TransactionDataValidationError, match="default_timezone"):
        preprocess_transaction_data(data)


def test_naive_timestamp_accepts_explicit_timezone(
    valid_transaction_data: pd.DataFrame,
) -> None:
    data = valid_transaction_data.assign(
        transaction_timestamp=["2026-08-01 14:00:00"] * 3
    )
    result = preprocess_transaction_data(
        data, default_timezone="America/Toronto"
    )
    assert result.loc[0, "transaction_timestamp"] == pd.Timestamp(
        "2026-08-01T18:00:00Z"
    )


def test_preprocessing_normalizes_optional_fields_and_fraud_labels(
    valid_transaction_data: pd.DataFrame,
) -> None:
    data = valid_transaction_data.assign(
        client_id=[101, 102, 101],
        merchant_category=[" grocery ", None, "retail"],
        transaction_type=[" purchase ", "refund", "purchase"],
        location=["store_001", None, "store_002"],
        transaction_outcome=[" approved ", "reversed", "approved"],
        fraud_label=["Yes", "0", None],
        fraud_label_source=[" manual_review ", "chargeback_feed", None],
        fraud_confirmed_at=["2026-08-04T12:00:00Z", None, None],
    )
    result = preprocess_transaction_data(data)

    assert str(result["client_id"].dtype) == "Int64"
    assert result["merchant_category"].tolist() == ["grocery", pd.NA, "retail"]
    assert result["fraud_label"].tolist() == [True, False, pd.NA]
    assert str(result["fraud_label"].dtype) == "boolean"
    assert result.loc[0, "fraud_label_source"] == "manual_review"
    assert str(result["fraud_confirmed_at"].dtype) == "datetime64[ns, UTC]"


@pytest.mark.parametrize(
    "labels",
    [
        [True, False, None],
        [1, 0, None],
        ["Yes", "No", None],
    ],
)
def test_supported_nullable_fraud_label_forms(
    valid_transaction_data: pd.DataFrame, labels: list[object]
) -> None:
    result = preprocess_transaction_data(valid_transaction_data.assign(fraud_label=labels))
    assert result["fraud_label"].tolist() == [True, False, pd.NA]


def test_invalid_fraud_label_fails_clearly(
    valid_transaction_data: pd.DataFrame,
) -> None:
    with pytest.raises(TransactionDataValidationError, match="ambiguous fraud labels"):
        preprocess_transaction_data(
            valid_transaction_data.assign(fraud_label=["likely", None, None])
        )


def test_preprocessing_is_immutable_and_preserves_rows(
    valid_transaction_data: pd.DataFrame,
) -> None:
    original = valid_transaction_data.copy(deep=True)
    result = preprocess_transaction_data(valid_transaction_data)
    pd.testing.assert_frame_equal(valid_transaction_data, original)
    assert len(result) == len(original)


def test_preprocessing_rejects_impossible_confirmation_time(
    valid_transaction_data: pd.DataFrame,
) -> None:
    data = valid_transaction_data.assign(
        fraud_label=[True, None, None],
        fraud_confirmed_at=["2026-08-01T13:00:00-04:00", None, None],
    )
    with pytest.raises(TransactionDataValidationError, match="before the transaction"):
        preprocess_transaction_data(data)
