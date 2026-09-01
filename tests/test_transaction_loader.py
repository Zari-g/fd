"""Tests for value-safe transaction CSV loading."""

from pathlib import Path

import pandas as pd
import pytest

from fraud_detection import load_transaction_data


def test_load_transaction_data_returns_dataframe(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    path.write_text("transaction_id,amount\ntxn_001,10.25\n", encoding="utf-8")

    result = load_transaction_data(path)

    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame(
            {
                "transaction_id": pd.Series(["txn_001"], dtype="string"),
                "amount": pd.Series(["10.25"], dtype="string"),
            }
        ),
    )


def test_load_transaction_data_preserves_amount_text_precision(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    path.write_text(
        "transaction_id,amount\ntxn_001,0.123456789012345678901\n",
        encoding="utf-8",
    )
    result = load_transaction_data(path)
    assert result.loc[0, "amount"] == "0.123456789012345678901"


def test_load_transaction_data_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_transaction_data(tmp_path / "missing.csv")


def test_load_transaction_data_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.touch()
    with pytest.raises(ValueError, match="CSV file is empty"):
        load_transaction_data(path)


def test_load_transaction_data_rejects_invalid_utf8_without_value_leak(
    tmp_path: Path,
) -> None:
    path = tmp_path / "invalid.csv"
    path.write_bytes(b"transaction_id\nPRIVATE-MARKER-\xff")
    with pytest.raises(ValueError, match="Could not read CSV file") as error:
        load_transaction_data(path)
    assert "PRIVATE-MARKER" not in str(error.value)
