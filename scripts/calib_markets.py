"""Build resolvable market table from Gamma API for calibration.

Usage: python scripts/calib_markets.py OUTDIR
Pulls closed markets with endDate in range, pages with limit/offset, polite delays.
Saves calibration/markets_*.csv.gz if small, else notes artifact. Resumable via progress.
"""
import csv
import datetime as dt
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

UA = {"User-Agent": "polymarket-btc-backtest/1.0 (research; github.com/CHUTSKO/polymarket-btc-backtest)"}
LIMIT = 100
START = "2026-04-14"
END = "2026-10-15"

def get_json(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except Exception as e:
            retry = not isinstance(e, urllib.error.HTTPError) or e.code in (429, 500, 502, 503, 504)
            if retry and i < tries - 1:
                time.sleep(min(2 ** (i + 1), 30))
                continue
            raise

def parse_json_field(s):
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        return []

def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "calibration"
    os.makedirs(outdir, exist_ok=True)
    prog = os.path.join(outdir, "markets_progress.json")
    offset = 0
    if os.path.exists(prog):
        with open(prog) as f:
            offset = json.load(f).get("offset", 0)
    markets = []
    excluded = Counter()
    while True:
        url = f"https://gamma-api.polymarket.com/markets?closed=true&limit={LIMIT}&offset={offset}&end_date_min={START}&end_date_max={END}"
        try:
            batch = get_json(url)
        except Exception as e:
            print(f"Failed at offset {offset}: {e}", flush=True)
            break
        if not batch:
            break
        for m in batch:
            try:
                prices = parse_json_field(m.get("outcomePrices"))
                tokens = parse_json_field(m.get("clobTokenIds"))
                outcomes = parse_json_field(m.get("outcomes"))
                if not prices or not tokens or len(prices) != len(tokens):
                    excluded["bad_fields"] += 1
                    continue
                winners = [i for i, p in enumerate(prices) if str(p) == "1"]
                if len(winners) != 1:
                    excluded["no_clear_winner"] += 1
                    continue
                wi = winners[0]
                end_str = m.get("endDate") or m.get("endDateIso") or ""
                try:
                    end_dt = dt.datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                except Exception:
                    excluded["bad_end"] += 1
                    continue
                cat = m.get("category") or "unknown"
                tags = ",".join([t.get("label", "") for t in (m.get("tags") or []) if isinstance(t, dict)])
                markets.append({
                    "condition_id": m.get("conditionId", ""),
                    "winner_token": tokens[wi],
                    "tokens": json.dumps(tokens),
                    "outcomes": json.dumps(outcomes),
                    "end_date": end_dt.isoformat(),
                    "category": cat,
                    "tags": tags,
                    "slug": m.get("slug", ""),
                    "volume": m.get("volume", ""),
                })
            except Exception:
                excluded["parse_error"] += 1
        offset += LIMIT
        with open(prog, "w") as f:
            json.dump({"offset": offset}, f)
        time.sleep(0.5)  # polite
        if len(batch) < LIMIT:
            break
    # save
    path = os.path.join(outdir, "markets.csv.gz")
    with gzip.open(path, "wt", newline="") as f:
        if markets:
            w = csv.DictWriter(f, fieldnames=markets[0].keys())
            w.writeheader()
            w.writerows(markets)
    with open(os.path.join(outdir, "markets_excluded.json"), "w") as f:
        json.dump(dict(excluded), f)
    print(f"Markets: {len(markets)}, excluded: {dict(excluded)}")

if __name__ == "__main__":
    main()
