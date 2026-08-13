"""Tests for card/account preprocessing and its sensitive-data boundary."""

import pandas as pd
import pytest

from fraud_detection import prepare_card_features, preprocess_card_data
from fraud_detection.preprocessing import CardDataValidationError


def test_preprocess_card_data_normalizes_analysis_types(
    valid_card_data: pd.DataFrame,
) -> None:
    result = preprocess_card_data(valid_card_data)

    assert str(result["credit_limit"].dtype) == "Float64"
    assert result["credit_limit"].tolist() == [1000.5, 2500.0]
    assert str(result["acct_open_date"].dtype) == "datetime64[ns]"
    assert result.loc[0, "acct_open_date"] == pd.Timestamp("2002-09-01")
    assert str(result["expires"].dtype) == "period[M]"
    assert result.loc[0, "expires"] == pd.Period("2030-12", freq="M")
    assert str(result["has_chip"].dtype) == "boolean"
    assert result["has_chip"].tolist() == [True, False]
    assert result["card_on_dark_web"].tolist() == [False, False]
    assert str(result["year_pin_last_changed"].dtype) == "Int64"


def test_preprocess_normalizes_categories_and_derives_safe_fields(
    valid_card_data: pd.DataFrame,
) -> None:
    result = preprocess_card_data(valid_card_data)

    assert result["card_brand"].tolist() == ["Visa", "Mastercard"]
    assert result["card_type"].tolist() == ["Credit", "Debit"]
    assert result["account_open_year"].tolist() == [2002, 2020]
    assert result["account_open_month"].tolist() == [9, 1]


def test_preprocess_does_not_modify_input(valid_card_data: pd.DataFrame) -> None:
    original = valid_card_data.copy(deep=True)

    preprocess_card_data(valid_card_data)

    pd.testing.assert_frame_equal(valid_card_data, original)


def test_preprocess_preserves_row_count(valid_card_data: pd.DataFrame) -> None:
    result = preprocess_card_data(valid_card_data)

    assert len(result) == len(valid_card_data)


def test_preprocess_rejects_invalid_values_explicitly(
    valid_card_data: pd.DataFrame,
) -> None:
    invalid = valid_card_data.copy()
    invalid.loc[0, "credit_limit"] = "invalid"

    with pytest.raises(CardDataValidationError, match="schema validation"):
        preprocess_card_data(invalid)


def test_prepare_card_features_removes_sensitive_fields(
    valid_card_data: pd.DataFrame,
) -> None:
    safe = prepare_card_features(valid_card_data)

    assert "card_number" not in safe.columns
    assert "cvv" not in safe.columns
    assert "id" in safe.columns
    assert "client_id" in safe.columns
    assert len(safe) == len(valid_card_data)
