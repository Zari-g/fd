# In-Store Transaction Fraud Detection

A Python package establishing secure card and transaction data foundations for
future in-store fraud detection. Iteration 3 provides transaction loading,
value-safe validation, deterministic normalization, duplicate detection,
card-link integrity, aggregate summaries, and explicit in-store filtering.
It intentionally implements no fraud model, score, risk rule, or feature
engineering.

Python 3.10 or newer is required:

```bash
python -m pip install -e ".[dev]"
```

## Secure architecture

```text
RAW CARD DATA
      -> card schema validation
      -> card preprocessing
      -> sensitive-field removal
      -> SAFE CARD TABLE
              |
              | cards.id
              v
RAW TRANSACTIONS -> schema and domain validation
                 -> transaction normalization
                 -> duplicate checks
                 -> card-link integrity
                 -> safe transaction table
                 -> explicit in-store subset
                 -> FUTURE FEATURE ENGINEERING
```

Treat any source containing `card_number` or `cvv` as sensitive. Raw/local
datasets belong under ignored paths such as `data/raw/` or `data/private/`.
Never put credential values in logs, exceptions, documentation, tests, or
reports. Transactions link only through `transactions.card_id -> cards.id`.

## Usage

```python
from fraud_detection import (
    filter_in_store_transactions,
    load_card_data,
    load_transaction_data,
    prepare_card_features,
    preprocess_transaction_data,
    validate_card_transaction_links,
)

raw_cards = load_card_data("data/raw/cards_data.csv")
cards = prepare_card_features(raw_cards)

raw_transactions = load_transaction_data("data/raw/transactions.csv")
transactions = preprocess_transaction_data(
    raw_transactions,
    default_timezone="America/Toronto",
)

link_report = validate_card_transaction_links(cards, transactions)
in_store = filter_in_store_transactions(transactions)
```

The timezone is caller-supplied; the package has no default. Offset-aware and
explicitly localized timestamps become UTC-aware pandas datetimes. Amounts
become exact `Decimal` objects in `amount`; they are never silently rounded or
converted between currencies. See the complete
[transaction contract](docs/transaction_schema.md).

## Public API

```python
from fraud_detection import (
    filter_in_store_transactions,
    find_transaction_duplicates,
    load_card_data,
    load_transaction_data,
    prepare_card_features,
    preprocess_card_data,
    preprocess_transaction_data,
    summarize_dataset,
    summarize_transactions,
    validate_card_schema,
    validate_card_transaction_links,
    validate_dataset,
    validate_transaction_schema,
)
```

All Iteration 1 and 2 APIs remain available. Validation and integrity reports
contain structured counts and column names, not row values. Transformations
return new DataFrames and do not silently remove duplicates.

## Data assets and limitations

`data/sample_cards.csv` and `data/sample_transactions.csv` are tiny,
credential-free synthetic examples for exercising software behavior. There is
no genuine transaction dataset in this repository, and the samples do not
represent a realistic fraud distribution or validate fraud-detection
effectiveness.

## Tests

```bash
python -m pytest
```

## Roadmap

1. **Complete:** package foundation, generic CSV loading, validation, summaries.
2. **Complete:** secure card schemas, typed preprocessing, sensitive-data removal.
3. **Complete:** transaction ingestion, normalization, integrity, safe summaries.
4. Next: leakage-safe transaction feature infrastructure can be designed with
   synthetic fixtures; empirical fraud analysis, training, and evaluation must
   wait for suitable genuine transaction data and documented labels.
