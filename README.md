# In-Store Transaction Fraud Detection

A Python package establishing secure, reusable data foundations for future
in-store transaction fraud detection. **Iteration 2** provides explicit card
data schemas, structured validation, typed preprocessing, and a sensitive-data
boundary. Fraud rules, labels, scoring, and models are intentionally not yet
implemented because the current source is card/account reference data rather
than transactions.

## Installation

Python 3.10 or newer is required:

```bash
python -m pip install -e ".[dev]"
```

For runtime use without test dependencies:

```bash
python -m pip install -e .
```

## Secure data handling

Treat any source containing `card_number` or `cvv` as sensitive, even when it
is described as synthetic. Raw and local datasets belong under ignored paths
such as `data/raw/` or `data/private/`; never put their values in logs,
exceptions, documentation, notebooks, reports, tests, or issues. The repository
tracks only a credential-free analytical sample.

The supported boundary is:

```text
Raw data
    -> schema validation
    -> normalization / preprocessing
    -> sensitive-field removal
    -> safe analytical dataset
    -> future feature engineering
    -> future fraud detection
```

`preprocess_card_data` intentionally retains sensitive fields in its intermediate
result so normalization and removal are separate, auditable stages. Do not use
that intermediate result for analysis. `prepare_card_features` performs both
stages and returns the safe representation.

## Usage

```python
from fraud_detection import (
    load_card_data,
    prepare_card_features,
    preprocess_card_data,
    validate_card_schema,
)

raw_df = load_card_data("data/raw/cards_data.csv")
schema_report = validate_card_schema(raw_df)

if schema_report["is_valid"]:
    normalized_df = preprocess_card_data(raw_df)  # restricted intermediate
    safe_df = prepare_card_features(raw_df)       # use for analysis
```

Validation returns `is_valid`, row count, missing and unexpected column names,
and structured issues containing only aggregate counts. It never includes cell
values. Schema drift, empty required values, malformed numeric/currency/date or
boolean fields, implausible PIN-change years, negative limits, and duplicate
card-record IDs are reported explicitly. Preprocessing refuses invalid input
instead of silently coercing it.

Normalized representations are:

- identifiers and integer counts: pandas nullable `Int64`;
- `credit_limit`: nullable `Float64`;
- boolean-like fields: nullable `boolean`;
- `expires`: monthly `Period[M]` with no invented day;
- `acct_open_date`: `datetime64[ns]`, using the first day of the source month
  solely as a pandas storage convention;
- categories: trimmed and normalized for casing without category merging;
- derived `account_open_year` and `account_open_month` fields.

The older `validate_dataset` and `summarize_dataset` APIs remain available for
generic structural inspection.

## Public API

```python
from fraud_detection import (
    load_card_data,
    prepare_card_features,
    preprocess_card_data,
    summarize_dataset,
    validate_card_schema,
    validate_dataset,
)
```

Lower-level schema constants and `drop_sensitive_fields` remain available from
their focused subpackages rather than being added to the package root.

## Data assets

`data/sample_cards.csv` is a small, clearly synthetic example of the safe
analytical output. It omits payment-card numbers and verification values. Unit
tests construct their own non-credential fixtures.

The original card source has 6,146 records and 13 columns but no transaction
events and no usable fraud target. See [the future transaction contract](docs/transaction_schema.md)
for the minimum data needed next.

## Tests

```bash
python -m pytest
```

## Roadmap

1. **Complete:** package foundation, CSV loading, generic validation, summaries.
2. **Complete:** secure schemas, typed card preprocessing, sensitive-field removal.
3. **Next:** transaction ingestion and validation against the documented
   contract, including join-integrity checks and fraud-label provenance.
4. Later, after suitable labeled transaction data exists: leakage-safe feature
   engineering, baselines, evaluation, explainability, and deployment design.

No transaction behavior or fraud outcome is inferred from
`card_on_dark_web`; it is only a normalized card/account attribute.
