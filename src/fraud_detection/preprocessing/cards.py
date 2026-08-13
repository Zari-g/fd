"""Immutable normalization and sensitive-field removal for card data."""

import pandas as pd

from fraud_detection.data.schema import SENSITIVE_FIELDS
from fraud_detection.data.validation import (
    CardSchemaValidationResult,
    validate_card_schema,
)


class CardDataValidationError(ValueError):
    """Raised when raw card data cannot be safely preprocessed."""


_BOOLEAN_MAP = {
    "yes": True,
    "true": True,
    "1": True,
    "no": False,
    "false": False,
    "0": False,
}


def _validation_error_message(report: CardSchemaValidationResult) -> str:
    messages = [issue["message"] for issue in report["issues"]]
    return "Card data failed schema validation: " + " ".join(messages)


def _parse_credit_limit(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="raise").astype("Float64")


def _parse_boolean(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.casefold()
    return normalized.map(_BOOLEAN_MAP).astype("boolean")


def _normalize_category(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.title()


def preprocess_card_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize raw card/account data in a new DataFrame.

    ``acct_open_date`` uses a pandas timestamp set to the first day of the
    represented month; this is a storage convention and not claimed source
    precision. ``expires`` uses pandas' monthly ``Period`` dtype so no day is
    invented. Sensitive fields remain in this intermediate result and must not
    be used as analytical features; use :func:`prepare_card_features` to cross
    the sensitive-data boundary.

    Raises
    ------
    CardDataValidationError
        If any required value or schema constraint is invalid. Error messages
        contain aggregate counts only, never cell contents.
    """
    report = validate_card_schema(df)
    if not report["is_valid"]:
        raise CardDataValidationError(_validation_error_message(report))

    result = df.copy(deep=True)

    for column in ("id", "client_id", "num_cards_issued", "year_pin_last_changed"):
        result[column] = pd.to_numeric(result[column], errors="raise").astype("Int64")

    for column in SENSITIVE_FIELDS:
        result[column] = result[column].astype("string")

    result["credit_limit"] = _parse_credit_limit(result["credit_limit"])
    result["acct_open_date"] = pd.to_datetime(
        result["acct_open_date"].astype("string").str.strip(),
        format="%m/%Y",
        errors="raise",
    ).astype("datetime64[ns]")
    expiration_dates = pd.to_datetime(
        result["expires"].astype("string").str.strip(),
        format="%m/%Y",
        errors="raise",
    )
    result["expires"] = expiration_dates.dt.to_period("M")

    for column in ("has_chip", "card_on_dark_web"):
        result[column] = _parse_boolean(result[column])
    for column in ("card_brand", "card_type"):
        result[column] = _normalize_category(result[column])

    result["account_open_year"] = result["acct_open_date"].dt.year.astype("Int64")
    result["account_open_month"] = result["acct_open_date"].dt.month.astype("Int64")
    return result


def drop_sensitive_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy without raw payment-card fields.

    Both sensitive columns must be present so accidental schema drift fails
    closed rather than creating a partially sanitized analytical dataset.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    missing = [column for column in SENSITIVE_FIELDS if column not in df.columns]
    if missing:
        raise ValueError(
            f"Cannot establish sensitive-field boundary; {len(missing)} expected "
            "sensitive column(s) are missing."
        )
    return df.drop(columns=list(SENSITIVE_FIELDS)).copy(deep=True)


def prepare_card_features(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw card data and return its safe analytical representation."""
    return drop_sensitive_fields(preprocess_card_data(df))
