"""Public API for the fraud detection package."""

from fraud_detection.analysis.summary import summarize_dataset
from fraud_detection.data.loader import load_card_data
from fraud_detection.data.validation import validate_dataset

__all__ = ["load_card_data", "summarize_dataset", "validate_dataset"]
__version__ = "0.1.0"

