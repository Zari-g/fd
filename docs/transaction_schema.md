# Future transaction data contract

The project cannot perform genuine fraud detection from card/account reference
data alone. A future source must represent individual transaction events and
link them to cards through `transaction.card_id -> card.id`. `client_id` may be
included for efficient aggregation, but it is optional because the card table
already supplies it; if present, the two sources must agree.

## Required ingestion fields

| Field | Expected type | Purpose |
|---|---|---|
| `transaction_id` | unique identifier | Deduplicate and trace an event. |
| `card_id` | identifier | Join to the safe card-record identifier `id`. |
| `transaction_timestamp` | timezone-aware datetime | Preserve event ordering and local-time context. |
| `amount` | decimal/numeric currency amount | Represent signed transaction value under a documented convention. |
| `merchant_id` | identifier | Identify the merchant or store. |
| `channel` | categorical | Explicitly distinguish point-of-sale/in-store activity from online or other channels. |
| `currency` | ISO 4217 string | Interpret amount consistently and support conversion policy. |

## Optional but strongly useful fields

| Field | Expected type | Purpose |
|---|---|---|
| `client_id` | identifier | Denormalized cardholder/account link; validate against card data. |
| `merchant_category` | category/code | Describe merchant activity; may instead come from merchant reference data. |
| `transaction_type` | category | Purchase, refund, cash withdrawal, and similar event semantics. |
| `location` | structured location or reference | Store/city/region/coordinates, with privacy controls. |
| `transaction_outcome` | category | Approved, declined, reversed, or other processing result. |
| `fraud_label` | boolean/category | Confirmed fraud outcome; eventual supervised-learning target. |

`fraud_label` is optional for raw event ingestion and scoring-only flows, but it
is mandatory for supervised training and honest evaluation. Its provenance,
confirmation delay, review process, meaning, and as-of time must be documented
to prevent leakage. A decline is not automatically fraud, and a card attribute
such as `card_on_dark_web` is not a substitute target.

This contract is definition-only in Iteration 2. It does not fabricate events,
labels, transaction features, rules, or scores.
