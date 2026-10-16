# polymarket-btc-backtest

Research backtest: does buying the ~1¢ side of Polymarket's "Bitcoin Up or Down" 5-minute markets make money after
realistic fills and fees?

- Data: the free public [PMXT order-book archive](https://archive.pmxt.dev) and Polymarket's public Gamma API.
- Paper research only: no trading, no accounts, no API keys. Everything runs in GitHub Actions.

## What's here
- `coverage/`: which archive hours actually contain these markets (made by `scripts/coverage.py`).
- Backtest code and results will be added after the validation step passes.
