"""Generic and card-schema-specific dataset validation utilities."""

from datetime import datetime
import re
from typing import Any, Literal, TypedDict

import pandas as pd

from fraud_detection.data.schema import (
    BOOLEAN_LIKE_FIELDS,
    CARD_DATA_SCHEMA,
    DATE_LIKE_FIELDS,
    REQUIRED_COLUMNS,
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


_BOOLEAN_VALUES = frozenset({"yes", "no", "true", "false", "1", "0"})
_MONTH_YEAR_PATTERN = re.compile(r"^(0[1-9]|1[0-2])/\d{4}$")
_CURRENCY_PATTERN = re.compile(
    r"^\s*\$?\s*[+-]?(?:\d+(?:,\d{3})*|\d+)(?:\.\d+)?\s*$"
)


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
