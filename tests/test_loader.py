"""Tests for CSV loading."""

from pathlib import Path

import pandas as pd
import pytest

from fraud_detection import load_card_data


def test_load_card_data_returns_dataframe(tmp_path: Path) -> None:
    csv_path = tmp_path / "cards.csv"
    csv_path.write_text("card_id,amount\n1,12.50\n2,20.00\n", encoding="utf-8")

    result = load_card_data(csv_path)

    expected = pd.DataFrame({"card_id": [1, 2], "amount": [12.5, 20.0]})
    pd.testing.assert_frame_equal(result, expected)


def test_load_card_data_rejects_nonexistent_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_card_data(missing_path)


def test_load_card_data_rejects_empty_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.touch()

    with pytest.raises(ValueError, match="CSV file is empty"):
        load_card_data(csv_path)


def test_load_card_data_allows_header_only_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "headers.csv"
    csv_path.write_text("card_id,amount\n", encoding="utf-8")

    result = load_card_data(csv_path)

    assert result.empty
    assert list(result.columns) == ["card_id", "amount"]

