"""Aggregate-only transaction summaries and explicit in-store selection."""

from decimal import Decimal
from statistics import median
from typing import Any

import pandas as pd

from fraud_detection.data.integrity import find_transaction_duplicates


def _counts(series: pd.Series) -> dict[str, int]:
    return {
        str(value): int(count)
        for value, count in series.value_counts(dropna=False).items()
    }


def _amount_summary(series: pd.Series) -> dict[str, Decimal | None]:
    amounts = [value for value in series if not pd.isna(value)]
    if not amounts:
        return {
            "minimum": None,
            "maximum": None,
            "median": None,
            "mean": None,
            "total": None,
        }
    total = sum(amounts, Decimal("0"))
    return {
        "minimum": min(amounts),
        "maximum": max(amounts),
        "median": median(amounts),
        "mean": total / Decimal(len(amounts)),
        "total": total,
    }


def summarize_transactions(df: pd.DataFrame) -> dict[str, Any]:
    """Return aggregate-only statistics for normalized transactions."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    required = {
        "transaction_id",
        "card_id",
        "transaction_timestamp",
        "amount",
        "merchant_id",
        "channel",
        "currency",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"transactions are missing {len(missing)} required summary column(s)"
        )

    summary: dict[str, Any] = {
        "transaction_count": len(df),
        "unique_transaction_count": int(df["transaction_id"].nunique(dropna=True)),
        "unique_card_count": int(df["card_id"].nunique(dropna=True)),
        "unique_merchant_count": int(df["merchant_id"].nunique(dropna=True)),
        "timestamp_min": df["transaction_timestamp"].min() if len(df) else None,
        "timestamp_max": df["transaction_timestamp"].max() if len(df) else None,
        "currency_counts": _counts(df["currency"]),
        "channel_counts": _counts(df["channel"]),
        "duplicate_counts": find_transaction_duplicates(df),
        "amount": _amount_summary(df["amount"]),
        "label_available": "fraud_label" in df.columns,
    }

    if "fraud_label" in df.columns:
        labeled = df["fraud_label"].notna()
        labeled_count = int(labeled.sum())
        fraud_count = int(df["fraud_label"].eq(True).fillna(False).sum())
        non_fraud_count = int(df["fraud_label"].eq(False).fillna(False).sum())
        summary.update(
            {
                "labeled_transaction_count": labeled_count,
                "fraud_count": fraud_count,
                "non_fraud_count": non_fraud_count,
                "unlabeled_count": len(df) - labeled_count,
                "fraud_rate_among_labeled": (
                    fraud_count / labeled_count if labeled_count else None
                ),
            }
        )
    return summary


def filter_in_store_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Return a new frame containing only canonical ``in_store`` rows."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if "channel" not in df.columns:
        raise ValueError("transactions must contain a normalized 'channel' column")
    return df.loc[df["channel"].eq("in_store")].copy(deep=True)
