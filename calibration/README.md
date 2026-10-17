# Calibration plan

Follows grok/handoff/pmxt-calibration.md exactly where possible.

## Unverified assumptions
- Gamma API query params end_date_min / end_date_max / closed=true may not filter as expected; script pages all closed and filters client-side if needed. Fields relied on: conditionId, clobTokenIds (JSON string), outcomes (JSON), outcomePrices (JSON strings "1"/"0"), endDate (ISO), category, tags (list of dict with label), slug, volume. Fail loudly on missing.
- Fee rates from docs.polymarket.com/trading/fees as of 2026-10-17; categories not matching use gross only.
- Bootstrap approximates fee using average price; exact per-trade fee not recomputed from aggregates.
- Hour processing is sequential in Python loops for simplicity; may be slow for large batches.
- Coverage CSVs used to select hours 02:00 and 14:00 UTC where file=yes.

## Deviations
- Summarize script is partial: full month/half/stability/Bonferroni not fully implemented in this commit (skeleton for bootstrap and cells).
- Workflow hour job is placeholder; needs logic to select specific hours from coverage CSVs and call calib_hour.py for each in chunk.
- Tests are basic; not run here (no local execution environment for full suite).
- Markets table may exceed 5MB; saved as .gz, workflow uses artifact.

## Open questions
- Exact Gamma endpoint params for date range on closed markets.
- Whether all historical markets have outcomePrices as "1"/"0" strings for resolved.
- How to map arbitrary categories to fee rates if docs list is incomplete.
- Best way to keep per-market sums small when thousands of markets per hour.
