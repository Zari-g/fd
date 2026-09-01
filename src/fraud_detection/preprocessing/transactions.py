"""Immutable, timezone-safe normalization for transaction data."""

from decimal import Decimal
from typing import Any

import pandas as pd

from fraud_detection.data.validation import (
    CHANNEL_ALIASES,
    TransactionSchemaValidationResult,
    validate_transaction_schema,
)


class TransactionDataValidationError(ValueError):
    """Raised when transaction data cannot be interpreted safely."""


_FRAUD_LABEL_MAP: dict[str, bool] = {
    "true": True,
    "yes": True,
    "1": True,
    "1.0": True,
    "false": False,
    "no": False,
    "0": False,
    "0.0": False,
}


def _validation_error_message(report: TransactionSchemaValidationResult) -> str:
    errors = [
        issue["message"]
        for issue in report["issues"]
        if issue["severity"] == "error"
    ]
    return "Transaction data failed schema validation: " + " ".join(errors)


def _normalize_identifier(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _normalize_optional_text(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip()
    return normalized.mask(normalized.eq(""), pd.NA)


def _normalize_timestamp(
    series: pd.Series,
    *,
    column: str,
    default_timezone: str | None,
) -> pd.Series:
    normalized: list[pd.Timestamp | Any] = []
    naive_count = 0

    for value in series:
        if pd.isna(value):
            normalized.append(pd.NaT)
            continue

        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            naive_count += 1
            if default_timezone is None:
                normalized.append(timestamp)
                continue
            try:
                timestamp = timestamp.tz_localize(
                    default_timezone,
                    ambiguous="raise",
                    nonexistent="raise",
                )
            except (TypeError, ValueError) as exc:
                raise TransactionDataValidationError(
                    f"Column '{column}' contains local timestamps that cannot be "
                    "safely localized with the supplied timezone."
                ) from exc
        normalized.append(timestamp.tz_convert("UTC"))

    if naive_count and default_timezone is None:
        raise TransactionDataValidationError(
            f"Column '{column}' contains {naive_count} timezone-naive timestamp(s); "
            "supply default_timezone explicitly."
        )
    return pd.Series(pd.to_datetime(normalized, utc=True), index=series.index).astype(
        "datetime64[ns, UTC]"
    )


def _normalize_fraud_labels(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.casefold()
    return normalized.map(_FRAUD_LABEL_MAP).astype("boolean")


def preprocess_transaction_data(
    df: pd.DataFrame,
    *,
    default_timezone: str | None = None,
) -> pd.DataFrame:
    """Validate and normalize transaction data in a new DataFrame.

    Amounts remain in ``amount`` as exact :class:`decimal.Decimal` objects.
    No scale is imposed, no precision is rounded, and negative signed values
    remain available for source-defined refunds or reversals. Timestamps are
    converted to ``datetime64[ns, UTC]``. Naive timestamps require an explicit
    caller-supplied timezone; daylight-saving ambiguities are never guessed.
    """
    report = validate_transaction_schema(df)
    if not report["is_valid"]:
        raise TransactionDataValidationError(_validation_error_message(report))

    result = df.copy(deep=True)
    result["transaction_id"] = _normalize_identifier(result["transaction_id"])
    result["card_id"] = pd.to_numeric(result["card_id"], errors="raise").astype("Int64")
    result["merchant_id"] = _normalize_identifier(result["merchant_id"])
    if "client_id" in result.columns:
        result["client_id"] = pd.to_numeric(
            result["client_id"], errors="raise"
        ).astype("Int64")

    result["transaction_timestamp"] = _normalize_timestamp(
        result["transaction_timestamp"],
        column="transaction_timestamp",
        default_timezone=default_timezone,
    )
    if "fraud_confirmed_at" in result.columns:
        result["fraud_confirmed_at"] = _normalize_timestamp(
            result["fraud_confirmed_at"],
            column="fraud_confirmed_at",
            default_timezone=default_timezone,
        )

    result["amount"] = result["amount"].map(
        lambda value: Decimal(str(value).strip())
    )
    result["currency"] = result["currency"].astype("string").str.strip().str.upper()
    channel_keys = (
        result["channel"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .str.replace(r"[\s-]+", "_", regex=True)
    )
    result["channel"] = channel_keys.map(CHANNEL_ALIASES).astype("string")

    for column in (
        "merchant_category",
        "transaction_type",
        "location",
        "transaction_outcome",
        "fraud_label_source",
    ):
        if column in result.columns:
            result[column] = _normalize_optional_text(result[column])
    if "fraud_label" in result.columns:
        result["fraud_label"] = _normalize_fraud_labels(result["fraud_label"])

    if "fraud_confirmed_at" in result.columns:
        impossible = (
            result["fraud_confirmed_at"].notna()
            & result["transaction_timestamp"].notna()
            & (result["fraud_confirmed_at"] < result["transaction_timestamp"])
        )
        count = int(impossible.sum())
        if count:
            raise TransactionDataValidationError(
                f"Transaction data failed timing validation: {count} row(s) "
                "confirm fraud before the transaction occurred."
            )

    return result
