# In-Store Transaction Fraud Detection

A Python package for building clear, reusable in-store transaction fraud
detection workflows. This repository is currently in its **foundation
iteration**: it provides data loading, generic validation, and exploratory
summaries. Fraud rules, feature engineering, and models are intentionally not
implemented yet.

## Installation

Python 3.10 or newer is required. From the repository root, create and activate
a virtual environment, then install the project and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

For runtime use without test dependencies:

```bash
python -m pip install -e .
```

## Basic usage

```python
from fraud_detection import load_card_data, summarize_dataset

df = load_card_data("cards_data.csv")
summary = summarize_dataset(df)
print(summary["row_count"], summary["column_count"])
```

`load_card_data` does not modify the source file or rename columns; pandas'
standard CSV type inference is used. Use `validate_dataset(df)` for a reusable
report covering shape, missing values, duplicates, dtypes, empty datasets, and
completely empty columns.

## Package structure

```text
.
|-- src/fraud_detection/
|   |-- analysis/       # Reusable exploratory summaries
|   |-- data/           # Loading and validation
|   `-- utils/          # Reserved for shared utilities
|-- tests/              # Focused unit tests
|-- data/               # Data documentation and future local assets
`-- notebooks/          # Future exploratory notebooks
```

## Dataset note

The supplied `cards_data.csv` contains 6,146 card records and 13 columns. It is
card/account reference data rather than transaction-level data, and it does not
contain a usable fraud outcome label. Some fields resemble payment-card data,
including card numbers and CVVs; handle the file as sensitive and do not expose
raw values in notebooks, logs, issues, or examples.

## Tests

```bash
python -m pytest
```

Tests use small temporary datasets and do not depend on the supplied source CSV.

## Roadmap

Future iterations may add explicit schemas and normalization, transaction data
support, fraud-oriented features and rules, model training and evaluation,
explainability, visualization, and batch or real-time scoring. These capabilities
will be added incrementally as suitable transaction data and outcome definitions
become available.
