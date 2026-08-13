"""Public API for the fraud detection package."""

from fraud_detection.analysis.summary import summarize_dataset
from fraud_detection.data.loader import load_card_data
from fraud_detection.data.validation import validate_card_schema, validate_dataset
from fraud_detection.preprocessing.cards import (
    prepare_card_features,
    preprocess_card_data,
)

__all__ = [
    "load_card_data",
    "prepare_card_features",
    "preprocess_card_data",
    "summarize_dataset",
    "validate_card_schema",
    "validate_dataset",
]
__version__ = "0.2.0"
