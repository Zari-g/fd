"""Shared synthetic fixtures with no payment credentials."""

import pandas as pd
import pytest


@pytest.fixture
def valid_card_data() -> pd.DataFrame:
    """Return raw-shaped data using unmistakable non-credential placeholders."""
    return pd.DataFrame(
        {
            "id": [1, 2],
            "client_id": [101, 102],
            "card_brand": [" visa ", "MASTERCARD"],
            "card_type": [" credit ", "DEBIT"],
            "card_number": ["FAKE-CARD-A", "FAKE-CARD-B"],
            "expires": ["12/2030", "01/2031"],
            "cvv": ["NOT-STORED", "NOT-STORED"],
            "has_chip": ["YES", "no"],
            "num_cards_issued": [1, 2],
            "credit_limit": ["$1,000.50", "$2500"],
            "acct_open_date": ["09/2002", "01/2020"],
            "year_pin_last_changed": [2020, 2024],
            "card_on_dark_web": ["No", "NO"],
        }
    )


@pytest.fixture
def valid_transaction_data() -> pd.DataFrame:
    """Return a raw-shaped, fully synthetic transaction dataset."""
    return pd.DataFrame(
        {
            "transaction_id": [" txn_001 ", "txn_002", "txn_003"],
            "card_id": [1, 2, 1],
            "transaction_timestamp": [
                "2026-08-01T14:21:13-04:00",
                "2026-08-02T10:00:00-04:00",
                "2026-08-03T18:30:00-04:00",
            ],
            "amount": ["10.25", "-2.50", "100"],
            "merchant_id": [" merchant_001 ", "merchant_002", "merchant_001"],
            "channel": ["POS", "online", "in-store"],
            "currency": ["cad", "USD", "cad"],
        }
    )
