"""Generic and card-schema-specific dataset validation utilities."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Literal, TypedDict

import pandas as pd

from fraud_detection.data.schema import (
    BOOLEAN_LIKE_FIELDS,
    CARD_DATA_SCHEMA,
    DATE_LIKE_FIELDS,
    REQUIRED_COLUMNS,
    TRANSACTION_DATA_SCHEMA,
    TRANSACTION_REQUIRED_FIELDS,
)


class SchemaIssue(TypedDict):
    """A value-safe schema issue that never includes cell contents."""

    severity: Literal["error", "warning"]
    code: str
    column: str | None
    count: int
    message: str


class CardSchemaValidationResult(TypedDict):
    """Structured result returned by :func:`validate_card_schema`."""

    is_valid: bool
    row_count: int
    missing_columns: list[str]
    unexpected_columns: list[str]
    issues: list[SchemaIssue]


class TransactionSchemaValidationResult(TypedDict):
    """Structured result returned by :func:`validate_transaction_schema`."""

    is_valid: bool
    row_count: int
    missing_columns: list[str]
    unexpected_columns: list[str]
    issues: list[SchemaIssue]


_BOOLEAN_VALUES = frozenset({"yes", "no", "true", "false", "1", "0"})
_MONTH_YEAR_PATTERN = re.compile(r"^(0[1-9]|1[0-2])/\d{4}$")
_CURRENCY_PATTERN = re.compile(
    r"^\s*\$?\s*[+-]?(?:\d+(?:,\d{3})*|\d+)(?:\.\d+)?\s*$"
)
_AMOUNT_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Za-z]{3}$")
_TRANSACTION_BOOLEAN_VALUES = frozenset(
    {"yes", "no", "true", "false", "1", "0", "1.0", "0.0"}
)
CHANNEL_ALIASES: dict[str, str] = {
    "in_store": "in_store",
    "instore": "in_store",
    "pos": "in_store",
    "point_of_sale": "in_store",
    "online": "online",
    "ecommerce": "online",
    "mobile": "mobile",
    "atm": "atm",
    "other": "other",
}


def _empty_mask(series: pd.Series) -> pd.Series:
    """Return a mask for null or whitespace-only values."""
    mask = series.isna()
    if pd.api.types.is_object_dtype(series.dtype) or isinstance(
        series.dtype, pd.StringDtype
    ):
        mask = mask | series.astype("string").str.strip().eq("").fillna(False)
    return mask


def _issue(code: str, column: str | None, count: int, message: str) -> SchemaIssue:
    return {
        "severity": "error",
        "code": code,
        "column": column,
        "count": count,
        "message": message,
    }


def _warning(code: str, column: str | None, count: int, message: str) -> SchemaIssue:
    return {
        "severity": "warning",
        "code": code,
        "column": column,
        "count": count,
        "message": message,
    }


def _invalid_integer_mask(series: pd.Series) -> pd.Series:
    nonempty = ~_empty_mask(series)
    numeric = pd.to_numeric(series, errors="coerce")
    return nonempty & (numeric.isna() | numeric.mod(1).ne(0))


def _invalid_boolean_mask(series: pd.Series) -> pd.Series:
    nonempty = ~_empty_mask(series)
    normalized = series.astype("string").str.strip().str.casefold()
    return nonempty & ~normalized.isin(_BOOLEAN_VALUES)


def _invalid_month_year_mask(series: pd.Series) -> pd.Series:
    nonempty = ~_empty_mask(series)
    normalized = series.astype("string").str.strip()
    has_expected_shape = normalized.str.fullmatch(_MONTH_YEAR_PATTERN).fillna(False)
    parsed = pd.to_datetime(normalized, format="%m/%Y", errors="coerce")
    return nonempty & (~has_expected_shape | parsed.isna())


def _invalid_currency_mask(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    nonempty = ~_empty_mask(series)
    normalized = series.astype("string")
    has_expected_shape = normalized.str.fullmatch(_CURRENCY_PATTERN).fillna(False)
    cleaned = normalized.str.replace("$", "", regex=False).str.replace(
        ",", "", regex=False
    ).str.strip()
    numeric = pd.to_numeric(cleaned, errors="coerce")
    malformed = nonempty & (~has_expected_shape | numeric.isna())
    negative = nonempty & numeric.lt(0).fillna(False)
    return malformed, negative


def _normalized_channel(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.casefold()
        .str.replace(r"[\s-]+", "_", regex=True)
    )


def _invalid_amount_mask(series: pd.Series) -> pd.Series:
    """Return rows that cannot be represented as finite Decimal values."""
    nonempty = ~_empty_mask(series)

    def is_invalid(value: object) -> bool:
        if pd.isna(value):
            return False
        text = str(value).strip()
        if not _AMOUNT_PATTERN.fullmatch(text):
            return True
        try:
            return not Decimal(text).is_finite()
        except InvalidOperation:
            return True

    return nonempty & series.map(is_invalid)


def _invalid_datetime_mask(series: pd.Series) -> pd.Series:
    nonempty = ~_empty_mask(series)

    def is_invalid(value: object) -> bool:
        if pd.isna(value):
            return False
        try:
            pd.Timestamp(value)
        except (TypeError, ValueError, OverflowError):
            return True
        return False

    return nonempty & series.map(is_invalid)


def validate_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """Return basic structural and data-quality checks for a DataFrame.

    The function reports observations rather than enforcing a domain-specific
    schema, making it suitable for datasets added in future iterations.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    return {
        "shape": df.shape,
        "is_empty": df.empty,
        "missing_values": {
            column: int(count) for column, count in df.isna().sum().items()
        },
        "duplicate_rows": int(df.duplicated().sum()),
        "column_dtypes": {
            column: str(dtype) for column, dtype in df.dtypes.items()
        },
        "completely_empty_columns": [
            column for column in df.columns if df[column].isna().all()
        ],
    }


def validate_card_schema(df: pd.DataFrame) -> CardSchemaValidationResult:
    """Validate raw card/account data without exposing any cell values.

    Unexpected columns are errors so schema drift cannot silently enter the
    preprocessing pipeline. The returned issues contain only column names and
    aggregate row counts, including for sensitive fields.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    actual_columns = set(df.columns)
    expected_columns = set(REQUIRED_COLUMNS)
    missing_columns = sorted(expected_columns - actual_columns)
    unexpected_columns = sorted(actual_columns - expected_columns)
    issues: list[SchemaIssue] = []

    if df.empty:
        issues.append(
            _issue(
                "empty_dataset",
                None,
                0,
                "The card dataset contains no rows.",
            )
        )
    if missing_columns:
        issues.append(
            _issue(
                "missing_required_columns",
                None,
                len(missing_columns),
                f"{len(missing_columns)} required column(s) are missing.",
            )
        )
    if unexpected_columns:
        issues.append(
            _issue(
                "unexpected_columns",
                None,
                len(unexpected_columns),
                f"{len(unexpected_columns)} unexpected column(s) were found.",
            )
        )

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            continue
        empty_count = int(_empty_mask(df[column]).sum())
        if empty_count:
            qualifier = "sensitive " if CARD_DATA_SCHEMA[column].sensitive else ""
            issues.append(
                _issue(
                    "empty_required_values",
                    column,
                    empty_count,
                    f"{empty_count} rows contain empty values in {qualifier}column '{column}'.",
                )
            )

    integer_columns = ("id", "client_id", "num_cards_issued", "year_pin_last_changed")
    for column in integer_columns:
        if column not in df.columns:
            continue
        invalid_count = int(_invalid_integer_mask(df[column]).sum())
        if invalid_count:
            issues.append(
                _issue(
                    "invalid_integer",
                    column,
                    invalid_count,
                    f"{invalid_count} rows contain invalid integer values in column '{column}'.",
                )
            )

    for column in ("id", "client_id"):
        if column in df.columns:
            numeric = pd.to_numeric(df[column], errors="coerce")
            invalid_count = int(numeric.lt(0).fillna(False).sum())
            if invalid_count:
                issues.append(
                    _issue(
                        "negative_identifier",
                        column,
                        invalid_count,
                        f"{invalid_count} rows contain negative identifiers in column '{column}'.",
                    )
                )

    if "num_cards_issued" in df.columns:
        numeric = pd.to_numeric(df["num_cards_issued"], errors="coerce")
        invalid_count = int(numeric.lt(1).fillna(False).sum())
        if invalid_count:
            issues.append(
                _issue(
                    "invalid_card_count",
                    "num_cards_issued",
                    invalid_count,
                    f"{invalid_count} rows contain card counts below one.",
                )
            )

    if "year_pin_last_changed" in df.columns:
        numeric = pd.to_numeric(df["year_pin_last_changed"], errors="coerce")
        current_year = datetime.now().year
        implausible = numeric.lt(1900) | numeric.gt(current_year)
        invalid_count = int(implausible.fillna(False).sum())
        if invalid_count:
            issues.append(
                _issue(
                    "implausible_year",
                    "year_pin_last_changed",
                    invalid_count,
                    f"{invalid_count} rows contain implausible PIN-change years.",
                )
            )

    if "id" in df.columns:
        nonempty_ids = df.loc[~_empty_mask(df["id"]), "id"]
        duplicate_count = int(nonempty_ids.duplicated(keep=False).sum())
        if duplicate_count:
            issues.append(
                _issue(
                    "duplicate_identifier",
                    "id",
                    duplicate_count,
                    f"{duplicate_count} rows have duplicated card record IDs.",
                )
            )

    for column in BOOLEAN_LIKE_FIELDS:
        if column in df.columns:
            invalid_count = int(_invalid_boolean_mask(df[column]).sum())
            if invalid_count:
                issues.append(
                    _issue(
                        "invalid_boolean",
                        column,
                        invalid_count,
                        f"{invalid_count} rows contain invalid boolean-like values in column '{column}'.",
                    )
                )

    for column in DATE_LIKE_FIELDS:
        if column in df.columns:
            invalid_count = int(_invalid_month_year_mask(df[column]).sum())
            if invalid_count:
                issues.append(
                    _issue(
                        "invalid_month_year",
                        column,
                        invalid_count,
                        f"{invalid_count} rows contain malformed month/year values in column '{column}'.",
                    )
                )

    if "credit_limit" in df.columns:
        malformed, negative = _invalid_currency_mask(df["credit_limit"])
        malformed_count = int(malformed.sum())
        negative_count = int(negative.sum())
        if malformed_count:
            issues.append(
                _issue(
                    "invalid_currency",
                    "credit_limit",
                    malformed_count,
                    f"{malformed_count} rows contain malformed credit-limit values.",
                )
            )
        if negative_count:
            issues.append(
                _issue(
                    "negative_credit_limit",
                    "credit_limit",
                    negative_count,
                    f"{negative_count} rows contain negative credit-limit values.",
                )
            )

    for column in ("card_brand", "card_type"):
        if column in df.columns:
            empty_count = int(_empty_mask(df[column]).sum())
            # The general required-value issue already reports these rows.
            if empty_count == len(df) and len(df) > 0:
                issues.append(
                    _issue(
                        "empty_categorical_domain",
                        column,
                        empty_count,
                        f"Required categorical column '{column}' has no populated values.",
                    )
                )

    return {
        "is_valid": not issues,
        "row_count": len(df),
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
        "issues": issues,
    }


def validate_transaction_schema(
    df: pd.DataFrame,
) -> TransactionSchemaValidationResult:
    """Validate transaction structure and domains without exposing row values.

    Naive timestamps are structurally valid here because timezone localization
    is an explicit preprocessing choice. Unexpected columns and unsafe domain
    values are errors. Fraud outcome provenance gaps are warnings so labeled
    legacy data remains ingestible while the leakage risk stays visible.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    expected = set(TRANSACTION_DATA_SCHEMA)
    actual = set(df.columns)
    missing_columns = sorted(set(TRANSACTION_REQUIRED_FIELDS) - actual)
    unexpected_columns = sorted(actual - expected)
    issues: list[SchemaIssue] = []

    if df.empty:
        issues.append(_issue("empty_dataset", None, 0, "The transaction dataset contains no rows."))
    if missing_columns:
        issues.append(
            _issue(
                "missing_required_columns",
                None,
                len(missing_columns),
                f"{len(missing_columns)} required transaction column(s) are missing.",
            )
        )
    if unexpected_columns:
        issues.append(
            _issue(
                "unexpected_columns",
                None,
                len(unexpected_columns),
                f"{len(unexpected_columns)} unexpected transaction column(s) were found.",
            )
        )

    for column in TRANSACTION_REQUIRED_FIELDS:
        if column not in df.columns:
            continue
        count = int(_empty_mask(df[column]).sum())
        if count:
            issues.append(
                _issue(
                    "empty_required_values",
                    column,
                    count,
                    f"{count} rows contain empty values in required column '{column}'.",
                )
            )

    if "transaction_id" in df.columns:
        populated = df.loc[~_empty_mask(df["transaction_id"]), "transaction_id"]
        count = int(populated.astype("string").str.strip().duplicated(keep=False).sum())
        if count:
            issues.append(
                _issue(
                    "duplicate_transaction_id",
                    "transaction_id",
                    count,
                    f"{count} rows have duplicated transaction IDs.",
                )
            )

    for column in ("card_id", "client_id"):
        if column not in df.columns:
            continue
        invalid = _invalid_integer_mask(df[column])
        numeric = pd.to_numeric(df[column], errors="coerce")
        invalid = invalid | ((~_empty_mask(df[column])) & numeric.lt(0).fillna(False))
        count = int(invalid.sum())
        if count:
            issues.append(
                _issue(
                    "invalid_card_id" if column == "card_id" else "invalid_client_id",
                    column,
                    count,
                    f"{count} rows contain invalid identifiers in column '{column}'.",
                )
            )

    for column in ("transaction_timestamp", "fraud_confirmed_at"):
        if column not in df.columns:
            continue
        count = int(_invalid_datetime_mask(df[column]).sum())
        if count:
            issues.append(
                _issue(
                    "invalid_timestamp",
                    column,
                    count,
                    f"{count} rows contain malformed timestamps in column '{column}'.",
                )
            )

    if "amount" in df.columns:
        count = int(_invalid_amount_mask(df["amount"]).sum())
        if count:
            issues.append(
                _issue(
                    "invalid_amount",
                    "amount",
                    count,
                    f"{count} rows contain malformed transaction amounts.",
                )
            )

    if "currency" in df.columns:
        populated = ~_empty_mask(df["currency"])
        valid = df["currency"].astype("string").str.strip().str.fullmatch(
            _CURRENCY_CODE_PATTERN
        ).fillna(False)
        count = int((populated & ~valid).sum())
        if count:
            issues.append(
                _issue(
                    "invalid_currency_code",
                    "currency",
                    count,
                    f"{count} rows contain invalid three-letter currency codes.",
                )
            )

    if "channel" in df.columns:
        populated = ~_empty_mask(df["channel"])
        count = int((populated & ~_normalized_channel(df["channel"]).isin(CHANNEL_ALIASES)).sum())
        if count:
            issues.append(
                _issue(
                    "invalid_channel",
                    "channel",
                    count,
                    f"{count} rows contain unsupported transaction channels.",
                )
            )

    if "fraud_label" in df.columns:
        populated = ~_empty_mask(df["fraud_label"])
        normalized = df["fraud_label"].astype("string").str.strip().str.casefold()
        count = int((populated & ~normalized.isin(_TRANSACTION_BOOLEAN_VALUES)).sum())
        if count:
            issues.append(
                _issue(
                    "invalid_fraud_label",
                    "fraud_label",
                    count,
                    f"{count} rows contain ambiguous fraud labels.",
                )
            )
        source_missing = (
            populated
            if "fraud_label_source" not in df.columns
            else populated & _empty_mask(df["fraud_label_source"])
        )
        source_missing_count = int(source_missing.sum())
        if source_missing_count:
            issues.append(
                _warning(
                    "missing_fraud_label_source",
                    "fraud_label_source",
                    source_missing_count,
                    f"{source_missing_count} labeled rows have no fraud-label provenance.",
                )
            )
        confirmation_missing = (
            populated
            if "fraud_confirmed_at" not in df.columns
            else populated & _empty_mask(df["fraud_confirmed_at"])
        )
        confirmation_missing_count = int(confirmation_missing.sum())
        if confirmation_missing_count:
            issues.append(
                _warning(
                    "missing_fraud_confirmation_time",
                    "fraud_confirmed_at",
                    confirmation_missing_count,
                    f"{confirmation_missing_count} labeled rows have no confirmation time.",
                )
            )

    if {"transaction_timestamp", "fraud_confirmed_at"}.issubset(df.columns):
        impossible_count = 0
        for transaction_value, confirmed_value in zip(
            df["transaction_timestamp"], df["fraud_confirmed_at"]
        ):
            if pd.isna(transaction_value) or pd.isna(confirmed_value):
                continue
            try:
                transaction_time = pd.Timestamp(transaction_value)
                confirmed_time = pd.Timestamp(confirmed_value)
                both_aware = transaction_time.tzinfo is not None and confirmed_time.tzinfo is not None
                both_naive = transaction_time.tzinfo is None and confirmed_time.tzinfo is None
                if (both_aware or both_naive) and confirmed_time < transaction_time:
                    impossible_count += 1
            except (TypeError, ValueError, OverflowError):
                continue
        if impossible_count:
            issues.append(
                _issue(
                    "fraud_confirmation_before_transaction",
                    "fraud_confirmed_at",
                    impossible_count,
                    f"{impossible_count} rows confirm fraud before the transaction occurred.",
                )
            )

    return {
        "is_valid": not any(issue["severity"] == "error" for issue in issues),
        "row_count": len(df),
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
        "issues": issues,
    }
