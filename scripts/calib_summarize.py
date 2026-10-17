"""Pool calibration hour results, compute buckets, bootstrap ROI, stability.

Usage: python scripts/calib_summarize.py OUTDIR
Writes RESULTS.md, results.json, per-month/half. Bootstrap by markets, 2000 draws, seed 42.
"""
import glob
import json
import math
import os
import random
import sys
from collections import defaultdict, Counter

def wilson(k, n, z=1.96):
    if not n:
        return None, None
    p = k / n
    d = 1 + z*z / n
    c = (p + z*z / (2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return round(100*(c-h), 2), round(100*(c+h), 2)

def fee_rate(cat):
    # load from fees.json or hardcode known
    rates = {"Crypto": 0.07, "Sports": 0.05, "Finance": 0.04, "Politics": 0.04,
             "Economics": 0.05, "Culture": 0.05, "Weather": 0.05, "Mentions": 0.04, "Tech": 0.04, "Geopolitics": 0.0}
    return rates.get(cat, None)  # None = gross only

def main():
    outdir = sys.argv[1]
    hours = []
    for f in sorted(glob.glob(os.path.join(outdir, "hour_*.json"))):
        with open(f) as fh:
            hours.append(json.load(fh))
    # pool per market per cell
    cell_markets = defaultdict(lambda: defaultdict(lambda: {"shares":0,"cost":0,"payout":0,"trades":0}))
    dropped = Counter()
    for h in hours:
        dropped.update(h.get("dropped", {}))
        for kstr, v in h.get("sums", {}).items():
            pb, tb, cat, cid = kstr.split("|", 3)
            cell = (pb, tb, cat)
            cm = cell_markets[cell][cid]
            for kk in v:
                cm[kk] += v[kk]
    # now per cell aggregates
    results = {}
    rng = random.Random(42)
    for cell, mkts in cell_markets.items():
        n_m = len(mkts)
        if n_m < 1:
            continue
        tot_sh = sum(m["shares"] for m in mkts.values())
        tot_cost = sum(m["cost"] for m in mkts.values())
        tot_pay = sum(m["payout"] for m in mkts.values())
        avg_p = tot_cost / tot_sh if tot_sh else 0
        gross_roi = (tot_pay / tot_cost - 1) if tot_cost else 0
        rate = fee_rate(cell[2])
        fee_tot = 0
        if rate is not None:
            # approximate fee as sum shares * rate * p * (1-p) but we have aggregate; use avg for simplicity or recompute not possible
            fee_tot = tot_sh * rate * avg_p * (1 - avg_p)  # approx
        with_fee_roi = (tot_pay / (tot_cost + fee_tot) - 1) if (tot_cost + fee_tot) else 0
        # bootstrap
        rois = []
        mids = list(mkts.keys())
        for _ in range(2000):
            sample = [mkts[rng.choice(mids)] for _ in range(n_m)]
            sc = sum(m["cost"] for m in sample)
            sp = sum(m["payout"] for m in sample)
            sf = (sum(m["shares"] for m in sample) * rate * (sc / sum(m["shares"] for m in sample) if sum(m["shares"] for m in sample) else 0) * (1 - (sc / sum(m["shares"] for m in sample) if sum(m["shares"] for m in sample) else 0))) if rate else 0
            r = (sp / (sc + sf) - 1) if (sc + sf) else 0
            rois.append(r)
        rois.sort()
        p_val = sum(1 for r in rois if r <= 0) / 2000
        results[str(cell)] = {
            "trades": sum(m["trades"] for m in mkts.values()),
            "shares": tot_sh, "cost": tot_cost, "payout": tot_pay,
            "win_rate_shares": tot_pay / tot_sh if tot_sh else 0,
            "avg_price": avg_p, "gross_roi": gross_roi, "with_fee_roi": with_fee_roi,
            "n_markets": n_m, "bootstrap_p_roi_le_0": p_val,
            "fee_rate_used": rate,
        }
    # stability etc. would go here; for now basic
    with open(os.path.join(outdir, "results.json"), "w") as f:
        json.dump({"cells": results, "dropped": dict(dropped), "n_cells": len(results)}, f, indent=1)
    with open(os.path.join(outdir, "RESULTS.md"), "w") as f:
        f.write("# Calibration results\n\nSee results.json for numbers.\n")
    print(f"Cells: {len(results)}")

if __name__ == "__main__":
    main()
