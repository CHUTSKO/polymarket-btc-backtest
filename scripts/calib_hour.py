"""Process one PMXT hour for calibration: last_trade_price only.

Usage: python scripts/calib_hour.py HOUR OUTDIR
Reads markets table, filters last_trade_price in Arrow, joins, buckets by price/time/category.
Writes additive per-market sums for later bootstrap. Memory under 3GB.
"""
import csv
import datetime as dt
import gzip
import json
import os
import sys
import time
from collections import defaultdict

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from pmxt_fetch import NotInArchive, fetch

PRICE_BUCKETS = [
    (0, 0.01, "<=1"), (0.01, 0.02, "1-2"), (0.02, 0.05, "2-5"), (0.05, 0.10, "5-10"),
    (0.10, 0.20, "10-20"), (0.20, 0.40, "20-40"), (0.40, 0.60, "40-60"),
    (0.60, 0.80, "60-80"), (0.80, 0.90, "80-90"), (0.90, 0.95, "90-95"),
    (0.95, 0.98, "95-98"), (0.98, 0.99, "98-99"), (0.99, 1.01, ">99"),
]
TIME_BUCKETS = [
    (0, 1, "<1h"), (1, 6, "1-6h"), (6, 24, "6-24h"), (24, 168, "1-7d"),
    (168, 720, "7-30d"), (720, 1e9, ">30d"),
]

def price_bucket(p):
    for lo, hi, name in PRICE_BUCKETS:
        if lo <= p < hi:
            return name
    return "other"

def time_bucket(h):
    for lo, hi, name in TIME_BUCKETS:
        if lo <= h < hi:
            return name
    return "other"

def load_markets(path):
    mkts = {}
    token_to = {}
    with gzip.open(path, "rt") as f:
        for row in csv.DictReader(f):
            cid = row["condition_id"]
            mkts[cid] = row
            for t in json.loads(row["tokens"]):
                token_to[t] = cid
    return mkts, token_to

def main():
    hour, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    tmp = f"/tmp/calib_{hour}.parquet"
    mpath = os.path.join(outdir, "markets.csv.gz")
    if not os.path.exists(mpath):
        print("No markets table", flush=True)
        return
    mkts, token_to = load_markets(mpath)
    try:
        n, rec = fetch(f"https://r2v2.pmxt.dev/polymarket_orderbook_{hour}.parquet", tmp)
    except NotInArchive:
        print(f"No file {hour}")
        return
    pf = pq.ParquetFile(tmp)
    need = ["timestamp", "event_type", "asset_id", "price", "size"]
    if any(c not in pf.schema_arrow.names for c in need):
        raise RuntimeError("missing columns")
    sums = defaultdict(lambda: defaultdict(float))
    counts = Counter() if False else defaultdict(int)  # placeholder
    dropped = defaultdict(int)
    for batch in pf.iter_batches(batch_size=500_000, columns=need):
        m = pc.equal(batch["event_type"], "last_trade_price")
        fb = batch.filter(m)
        if fb.num_rows == 0:
            continue
        for i in range(fb.num_rows):
            aid = fb["asset_id"][i].as_py()
            if aid not in token_to:
                dropped["unknown_token"] += 1
                continue
            cid = token_to[aid]
            mkt = mkts[cid]
            p = float(fb["price"][i].as_py() or 0)
            s = float(fb["size"][i].as_py() or 0)
            if s <= 0 or not (0 < p < 1):
                dropped["bad_trade"] += 1
                continue
            ts_ms = int(fb["timestamp"][i].as_py())
            ts = dt.datetime.fromtimestamp(ts_ms / 1000, dt.timezone.utc)
            end = dt.datetime.fromisoformat(mkt["end_date"])
            if ts >= end:
                dropped["after_end"] += 1
                continue
            h2e = (end - ts).total_seconds() / 3600
            pb = price_bucket(p)
            tb = time_bucket(h2e)
            cat = "updown" if "-updown-" in mkt["slug"] else mkt["category"]
            key = (pb, tb, cat, cid)
            won = aid == mkt["winner_token"]
            sums[key]["shares"] += s
            sums[key]["cost"] += s * p
            sums[key]["payout"] += s if won else 0
            sums[key]["trades"] += 1
    # write per-market additive
    outp = os.path.join(outdir, f"hour_{hour}.json")
    serial = {f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": v for k, v in sums.items()}
    with open(outp, "w") as f:
        json.dump({"hour": hour, "sums": serial, "dropped": dict(dropped)}, f)
    if os.path.exists(tmp):
        os.remove(tmp)
    print(f"{hour} done, markets {len(set(k[3] for k in sums))}")

if __name__ == "__main__":
    main()
