# polymarket-btc-backtest - instructions for Claude (and Grok)

PUBLIC repo. Chris's research backtest of Polymarket "Bitcoin Up or Down" 5-minute markets (buying the ~1c side).
Runs only in GitHub Actions on public data. No trading, no accounts, no API keys.

## Rules
- This repo is PUBLIC. Never commit or print secrets. The ntfy topic lives ONLY in the Actions secret `NTFY_TOPIC`:
  workflows read `${{ secrets.NTFY_TOPIC }}` into an env var and never echo it. Never write the topic in any file,
  commit message, issue, or log line.
- Workflows trigger only on push to main or manual dispatch. Never add pull_request / pull_request_target triggers.
- Notifications: ntfy push only, never email.
- Never commit raw parquet files or any file over ~5 MB.
- Be polite to the free PMXT archive: at most 6 parallel downloads across all workflows running at once.
- Strategy prompts and private notes stay in Chris's private repo CHUTSKO/btc-bot (`grok/handoff/`), not here.

## Layout
- `scripts/coverage.py` + `.github/workflows/coverage.yml`: request a scan by committing a new timestamp to
  `requests/coverage`; finished hours are skipped, so re-running resumes. Output: `coverage/coverage_<chunk>.csv`
  (one row per hour; `windows_in_file` = 0-12) and `coverage/windows_<chunk>.jsonl` (one line per 5-minute window
  with tokens, outcomes, `outcome_prices` (winner = "1"), and `in_file`). Use these instead of re-querying Gamma.
- `scripts/backtest.py HOUR OUTDIR`: one hour -> `OUTDIR/hour_HOUR.json` (additive sums, errors) and
  `OUTDIR/entries_HOUR.csv`. `scripts/summarize.py OUTDIR` pools them -> `SUMMARY.md`, `pooled.json` (ratios and
  Wilson 95% intervals are computed only after pooling). Core logic `run_token` is pure Python and unit-testable.
- `.github/workflows/validate.yml`: the 8 fixed validation hours (commit to `requests/validate` to run).
  `backtest.py` skips hours whose `hour_*.json` already finished without errors (set FORCE=1 to redo).
- `scripts/pmxt_fetch.py`: ALWAYS download archive files with `fetch()`. Downloads really do stall part-way
  (2026-06-07T14: 201 MB in 3 s, then a trickle); `fetch` reconnects and resumes with HTTP Range and verifies size.

## Verified data facts (from the private btc-bot probe, Oct 2026)
- `price_change.size` = NEW total size at that price (0 removes the level); `side` BUY = bids, SELL = asks.
- Order rows by `timestamp` (exchange ms) with a STABLE sort on (timestamp, file position). File order is not time
  order; `timestamp_received` is a coarse batch time - never order by it.
- A rebuilt book drifts (69-93% level agreement with the next snapshot), so anchor it to each row's
  `best_bid` / `best_ask`. Do not apply `last_trade_price` rows to the book.
- `fee_rate_bps` on trade rows was 1000 in April and 0 in May 2026 for these markets; current docs say Crypto taker
  fee = shares x 0.07 x p x (1-p). Unresolved: always report gross and with-fee results.

---

# Coding guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
