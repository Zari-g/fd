# Data directory

Only sanitized, non-sensitive examples may be committed here.

- `sample_cards.csv` illustrates the safe analytical card representation and
  deliberately omits raw payment-card numbers and verification values.
- `raw/`, `private/`, and `local/` are ignored locations for developer-owned
  source data. Their contents must not be committed.

Keep source, license or usage terms, schema, and handling controls documented
for every future dataset. Never commit production cardholder data, credentials,
or derived files that still contain sensitive payment fields.
