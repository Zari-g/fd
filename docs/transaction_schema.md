# Transaction data contract

Iteration 3 defines the ingestion and integrity boundary for transaction
events. It does not create fraud rules, scores, features, models, or evidence
of fraud-detection performance. The repository has no genuine transaction
dataset; `data/sample_transactions.csv` is a small software fixture only.

## Fields

Required fields are:

| Field | Representation after preprocessing | Purpose |
|---|---|---|
| `transaction_id` | trimmed pandas `string`, unique | Stable event identifier. |
| `card_id` | nullable `Int64` | Foreign key to the safe card table's `id`. |
| `transaction_timestamp` | `datetime64[ns, UTC]` | Event time as an unambiguous instant. |
| `amount` | exact `decimal.Decimal` object | Signed source amount without floating-point error or rounding. |
| `merchant_id` | trimmed pandas `string` | Merchant/store identifier, not a continuous feature. |
| `channel` | canonical pandas `string` | Explicit transaction channel. |
| `currency` | uppercase three-letter pandas `string` | Currency context; no conversion is performed. |

Optional fields are `client_id`, `merchant_category`, `transaction_type`,
`location`, `transaction_outcome`, `fraud_label`, `fraud_label_source`, and
`fraud_confirmed_at`. Optional text is trimmed and remains nullable.

The only supported card join is:

```text
transactions.card_id -> cards.id
```

`card_number` and `cvv` are never transaction join keys and are not accepted
as transaction schema fields. If a transaction includes `client_id`, link
validation also checks that it agrees with the client attached to the card.

## Timestamp policy

Offset-aware input is converted to UTC, preserving the represented instant.
Pandas uses one common timezone for a Series, so original textual offsets are
not retained as separate strings. A naive timestamp is rejected unless the
caller explicitly supplies `default_timezone`; there is no package default.
Ambiguous or nonexistent daylight-saving times fail rather than being guessed.
The same policy applies to `fraud_confirmed_at`.

For example:

```python
transactions = preprocess_transaction_data(
    raw_transactions,
    default_timezone="America/Toronto",
)
```

The Toronto timezone above is a caller choice, not a package assumption.

## Money policy

`amount` becomes a Python `Decimal` in the existing column. This is the
simplest correct representation while currencies with different minor-unit
scales may be ingested: the package applies no binary floating-point
conversion, quantization, silent rounding, FX lookup, or currency conversion.
Negative values remain valid because source-defined refunds and reversals may
be signed; their meaning comes from the source contract and optional
`transaction_type`.

## Channel policy

Accepted canonical channels are `in_store`, `online`, `mobile`, `atm`, and
`other`. The following explicit aliases normalize predictably:

- `POS`, `instore`, `in-store`, and `point_of_sale` -> `in_store`
- `ecommerce` -> `online`

Matching is case-insensitive and spaces/hyphens normalize to underscores.
Anything else is rejected. Unknown values are never treated as in-store.

## Fraud outcomes and as-of time

`fraud_label` is optional. When supplied, boolean values and the narrow forms
`True/False`, `1/0`, and `Yes/No` normalize to pandas nullable `boolean`;
blank values remain `pd.NA`, and ambiguous labels are rejected. A decline,
amount, channel, transaction outcome, or card attribute never implies fraud.

`fraud_label_source` preserves outcome provenance as text.
`fraud_confirmed_at` records when the outcome became known. Confirmation before
the transaction is an invalid timing relationship. These three fields are
future outcome information and must be excluded from any authorization-time
predictive feature matrix. No such matrix is built in this iteration.

## Duplicate and integrity semantics

Duplicate reporting counts rows involved in exact row duplication separately
from rows involved in duplicated transaction IDs. It reports counts only and
does not remove rows. Card-link reports expose aggregate match/mismatch counts,
never unknown identifiers or transaction records.
