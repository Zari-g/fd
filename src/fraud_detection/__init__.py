"""Public API for the fraud detection package."""

from fraud_detection.analysis.summary import summarize_dataset
from fraud_detection.analysis.transactions import (
    filter_in_store_transactions,
    summarize_transactions,
)
from fraud_detection.data.integrity import (
    find_transaction_duplicates,
    validate_card_transaction_links,
)
from fraud_detection.data.loader import load_card_data, load_transaction_data
from fraud_detection.data.validation import (
    validate_card_schema,
    validate_dataset,
    validate_transaction_schema,
)
from fraud_detection.preprocessing.cards import (
    prepare_card_features,
    preprocess_card_data,
)
from fraud_detection.preprocessing.transactions import preprocess_transaction_data

__all__ = [
    "filter_in_store_transactions",
    "find_transaction_duplicates",
    "load_card_data",
    "load_transaction_data",
    "prepare_card_features",
    "preprocess_card_data",
    "preprocess_transaction_data",
    "summarize_dataset",
    "summarize_transactions",
    "validate_card_schema",
    "validate_card_transaction_links",
    "validate_dataset",
    "validate_transaction_schema",
]
__version__ = "0.3.0"
