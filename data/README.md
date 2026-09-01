# Data directory

Only sanitized, non-sensitive examples may be committed here.

- `sample_cards.csv` illustrates the safe analytical card representation and
  deliberately omits raw payment-card numbers and verification values.
- `sample_transactions.csv` contains ten obviously synthetic events linked to
  the sample cards through `card_id -> id`. It exists only to exercise loading,
  normalization, integrity, summary, and filtering behavior. Its labels and
  channel mix are not a realistic fraud distribution.
- `raw/`, `private/`, and `local/` are ignored locations for developer-owned
  source data. Their contents must not be committed.

Keep source, license or usage terms, schema, and handling controls documented
for every future dataset. Never commit production cardholder data, credentials,
or derived files that still contain sensitive payment fields.

No genuine transaction dataset is currently tracked. The transaction sample
contains no card numbers, CVVs, names, emails, addresses, or phone numbers.
