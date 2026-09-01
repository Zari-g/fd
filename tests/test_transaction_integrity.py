"""Tests for duplicate detection and safe card-link integrity reports."""

import pandas as pd
import pytest

from fraud_detection import (
    find_transaction_duplicates,
    preprocess_transaction_data,
    validate_card_transaction_links,
)


@pytest.mark.parametrize(
    ("frame", "exact", "ids"),
    [
        (pd.DataFrame({"transaction_id": ["a", "b"], "x": [1, 2]}), 0, 0),
        (pd.DataFrame({"transaction_id": ["a", "a"], "x": [1, 1]}), 2, 2),
        (pd.DataFrame({"transaction_id": ["a", "a"], "x": [1, 2]}), 0, 2),
        (
            pd.DataFrame(
                {"transaction_id": ["a", "a", "b", "b"], "x": [1, 1, 2, 3]}
            ),
            2,
            4,
        ),
    ],
)
def test_duplicate_reporting(
    frame: pd.DataFrame, exact: int, ids: int
) -> None:
    original = frame.copy(deep=True)
    assert find_transaction_duplicates(frame) == {
        "exact_duplicate_count": exact,
        "duplicate_transaction_id_count": ids,
    }
    pd.testing.assert_frame_equal(frame, original)


def test_card_links_full_partial_and_no_match(
    valid_transaction_data: pd.DataFrame,
) -> None:
    transactions = preprocess_transaction_data(valid_transaction_data)
    cards = pd.DataFrame({"id": pd.Series([1, 2], dtype="Int64"), "client_id": [101, 102]})

    full = validate_card_transaction_links(cards, transactions)
    assert full["matched_transaction_count"] == 3
    assert full["match_rate"] == 1.0

    partial = validate_card_transaction_links(cards.iloc[[0]], transactions)
    assert partial["matched_transaction_count"] == 2
    assert partial["unmatched_transaction_count"] == 1
    assert partial["unknown_card_id_count"] == 1

    none = validate_card_transaction_links(
        pd.DataFrame({"id": [99], "client_id": [999]}), transactions
    )
    assert none["matched_transaction_count"] == 0
    assert none["match_rate"] == 0.0


def test_card_links_validate_client_consistency(
    valid_transaction_data: pd.DataFrame,
) -> None:
    transactions = preprocess_transaction_data(
        valid_transaction_data.assign(client_id=[101, 999, 101])
    )
    cards = pd.DataFrame({"id": [1, 2], "client_id": [101, 102]})
    report = validate_card_transaction_links(cards, transactions)
    assert report["client_id_mismatch_count"] == 1
    assert "999" not in repr(report)


def test_card_links_report_consistent_client_ids(
    valid_transaction_data: pd.DataFrame,
) -> None:
    transactions = preprocess_transaction_data(
        valid_transaction_data.assign(client_id=[101, 102, 101])
    )
    cards = pd.DataFrame({"id": [1, 2], "client_id": [101, 102]})
    assert validate_card_transaction_links(cards, transactions)[
        "client_id_mismatch_count"
    ] == 0
