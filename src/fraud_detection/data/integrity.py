"""Value-safe duplicate and relational-integrity checks for transactions."""

from typing import TypedDict

import pandas as pd


class TransactionDuplicateReport(TypedDict):
    """Counts of rows involved in each duplicate condition."""

    exact_duplicate_count: int
    duplicate_transaction_id_count: int


class CardTransactionLinkReport(TypedDict):
    """Aggregate integrity measures for the card foreign key."""

    transaction_count: int
    matched_transaction_count: int
    unmatched_transaction_count: int
    match_rate: float
    unique_cards_referenced: int
    unknown_card_id_count: int
    client_id_mismatch_count: int


def find_transaction_duplicates(df: pd.DataFrame) -> TransactionDuplicateReport:
    """Report rows involved in exact and transaction-ID duplicates.

    No duplicate records or identifier values are returned. Detection never
    removes or modifies rows.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if "transaction_id" not in df.columns:
        raise ValueError("transactions must contain a 'transaction_id' column")

    normalized_ids = df["transaction_id"].astype("string").str.strip()
    populated_ids = normalized_ids.notna() & normalized_ids.ne("")
    duplicate_ids = populated_ids & normalized_ids.duplicated(keep=False)
    return {
        "exact_duplicate_count": int(df.duplicated(keep=False).sum()),
        "duplicate_transaction_id_count": int(duplicate_ids.sum()),
    }


def validate_card_transaction_links(
    cards_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
) -> CardTransactionLinkReport:
    """Measure ``transactions.card_id -> cards.id`` referential integrity.

    Actual unknown IDs and mismatched records are deliberately omitted. Card
    numbers and CVVs are neither accepted nor required as join keys.
    """
    if not isinstance(cards_df, pd.DataFrame) or not isinstance(
        transactions_df, pd.DataFrame
    ):
        raise TypeError("cards_df and transactions_df must be pandas DataFrames")
    if "id" not in cards_df.columns:
        raise ValueError("cards_df must contain an 'id' column")
    if "card_id" not in transactions_df.columns:
        raise ValueError("transactions_df must contain a 'card_id' column")
    if cards_df["id"].isna().any() or cards_df["id"].duplicated().any():
        raise ValueError("cards_df must contain populated, unique card IDs")

    card_ids = cards_df["id"]
    transaction_card_ids = transactions_df["card_id"]
    matched = transaction_card_ids.notna() & transaction_card_ids.isin(card_ids)
    transaction_count = len(transactions_df)
    matched_count = int(matched.sum())
    unmatched_count = transaction_count - matched_count
    unknown_ids = transaction_card_ids.loc[~matched & transaction_card_ids.notna()]

    mismatch_count = 0
    if "client_id" in transactions_df.columns:
        if "client_id" not in cards_df.columns:
            raise ValueError(
                "cards_df must contain 'client_id' when transactions include it"
            )
        card_clients = cards_df.set_index("id")["client_id"]
        expected_clients = transaction_card_ids.map(card_clients)
        comparable = matched & transactions_df["client_id"].notna()
        mismatch_count = int(
            (comparable & transactions_df["client_id"].ne(expected_clients)).sum()
        )

    return {
        "transaction_count": transaction_count,
        "matched_transaction_count": matched_count,
        "unmatched_transaction_count": unmatched_count,
        "match_rate": matched_count / transaction_count if transaction_count else 0.0,
        "unique_cards_referenced": int(transaction_card_ids.dropna().nunique()),
        "unknown_card_id_count": int(unknown_ids.nunique()),
        "client_id_mismatch_count": mismatch_count,
    }
