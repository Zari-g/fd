"""Explicit schema contracts for card and future transaction data."""

from dataclasses import dataclass
from typing import Final, Literal


SemanticType = Literal[
    "boolean",
    "category",
    "currency",
    "datetime",
    "identifier",
    "integer",
    "month_year",
    "sensitive_text",
    "string",
]


@dataclass(frozen=True)
class FieldSchema:
    """Describe one field without coupling the schema to pandas dtypes."""

    semantic_type: SemanticType
    required: bool = True
    sensitive: bool = False
    unique: bool = False
    description: str = ""


CARD_DATA_SCHEMA: Final[dict[str, FieldSchema]] = {
    "id": FieldSchema("identifier", unique=True, description="Internal card record ID."),
    "client_id": FieldSchema("identifier", description="Internal client/account owner ID."),
    "card_brand": FieldSchema("category"),
    "card_type": FieldSchema("category"),
    "card_number": FieldSchema(
        "sensitive_text", sensitive=True, description="Raw payment card identifier."
    ),
    "expires": FieldSchema("month_year", description="Card expiration month."),
    "cvv": FieldSchema(
        "sensitive_text", sensitive=True, description="Raw verification value."
    ),
    "has_chip": FieldSchema("boolean"),
    "num_cards_issued": FieldSchema("integer"),
    "credit_limit": FieldSchema("currency"),
    "acct_open_date": FieldSchema("month_year", description="Account opening month."),
    "year_pin_last_changed": FieldSchema("integer"),
    "card_on_dark_web": FieldSchema("boolean"),
}

REQUIRED_COLUMNS: Final[tuple[str, ...]] = tuple(CARD_DATA_SCHEMA)
EXPECTED_SEMANTIC_TYPES: Final[dict[str, SemanticType]] = {
    name: definition.semantic_type for name, definition in CARD_DATA_SCHEMA.items()
}
IDENTIFIER_FIELDS: Final[tuple[str, ...]] = ("id", "client_id", "card_number")
SENSITIVE_FIELDS: Final[tuple[str, ...]] = ("card_number", "cvv")
NUMERIC_FIELDS: Final[tuple[str, ...]] = (
    "id",
    "client_id",
    "num_cards_issued",
    "credit_limit",
    "year_pin_last_changed",
)
CATEGORICAL_FIELDS: Final[tuple[str, ...]] = ("card_brand", "card_type")
DATE_LIKE_FIELDS: Final[tuple[str, ...]] = ("expires", "acct_open_date")
BOOLEAN_LIKE_FIELDS: Final[tuple[str, ...]] = ("has_chip", "card_on_dark_web")


# A future transaction source can be ingested without labels. ``fraud_label``
# becomes required only for supervised training or evaluation.
TRANSACTION_DATA_SCHEMA: Final[dict[str, FieldSchema]] = {
    "transaction_id": FieldSchema(
        "identifier", unique=True, description="Unique transaction/event ID."
    ),
    "card_id": FieldSchema(
        "identifier", description="Foreign key to card data field 'id'."
    ),
    "transaction_timestamp": FieldSchema(
        "datetime", description="Timezone-aware event time."
    ),
    "amount": FieldSchema("currency", description="Transaction amount."),
    "merchant_id": FieldSchema("identifier", description="Merchant or store ID."),
    "merchant_category": FieldSchema(
        "category",
        required=False,
        description="Merchant category code or normalized category.",
    ),
    "channel": FieldSchema(
        "category", description="POS/in-store channel discriminator."
    ),
    "currency": FieldSchema("string", description="ISO 4217 currency code."),
    "client_id": FieldSchema(
        "identifier", required=False, description="Optional denormalized client ID."
    ),
    "transaction_type": FieldSchema("category", required=False),
    "location": FieldSchema(
        "string", required=False, description="Store, city, region, or coordinates."
    ),
    "transaction_outcome": FieldSchema(
        "category", required=False, description="Approved, declined, or reversed."
    ),
    "fraud_label": FieldSchema(
        "boolean",
        required=False,
        description="Confirmed fraud outcome and eventual supervised target.",
    ),
}

TRANSACTION_REQUIRED_FIELDS: Final[tuple[str, ...]] = tuple(
    name for name, definition in TRANSACTION_DATA_SCHEMA.items() if definition.required
)
TRANSACTION_OPTIONAL_FIELDS: Final[tuple[str, ...]] = tuple(
    name for name, definition in TRANSACTION_DATA_SCHEMA.items() if not definition.required
)
