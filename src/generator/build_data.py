"""
AarogyaGrid — data builder.

Derives PHC inventory movements from epidemiology rather than inventing them.

Pipeline:
    1. Build facility registry (real districts, PHC/CHC norms)
    2. Generate weekly disease incidence (seasonality x population)
    3. Convert cases -> medicine consumption via clinical courses
    4. Simulate procurement (indent cycle, lead times, delays)
    5. Roll the stock ledger forward, allowing genuine stock-outs
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd
from datetime import date, timedelta

from src.config import (
    DISTRICTS, STATE, SKUS, SEASONALITY, BASE_INCIDENCE,NFHS_TREATMENT_RATE,
    PROFILE_SUPPLY, LEAD_TIME_MIN_DAYS, LEAD_TIME_MAX_DAYS,
    INDENT_CYCLE_DAYS, HISTORY_DAYS, RANDOM_SEED,
)

rng = np.random.default_rng(RANDOM_SEED)

OUT = os.path.join("data", "processed")
os.makedirs(OUT, exist_ok=True)

# District centroids (real coordinates); facilities are scattered around them.
CENTROIDS = {
    "Nalgonda":            (17.054, 79.267),
    "Yadadri Bhuvanagiri": (17.510, 78.900),
    "Suryapet":            (17.140, 79.623),
}

PHC_POP = 30_000      # Indian norm: 1 PHC per ~30,000 rural population
CHC_POP = 120_000     # 1 CHC per ~120,000


# ------------------------------------------------------------------ 1. facilities
def build_facilities():
    rows = []
    for d in DISTRICTS:
        lat0, lon0 = CENTROIDS[d["name"]]
        for i in range(d["phc"]):
            rows.append({
                "facility_id":   f"{d['name'][:3].upper()}-PHC-{i+1:02d}",
                "facility_name": f"PHC {d['name']} {i+1}",
                "facility_type": "PHC",
                "district":      d["name"],
                "state":         STATE,
                "profile":       d["profile"],
                "latitude":      round(lat0 + rng.uniform(-0.28, 0.28), 5),
                "longitude":     round(lon0 + rng.uniform(-0.28, 0.28), 5),
                "catchment_population": int(PHC_POP * rng.uniform(0.75, 1.30)),
            })
        for i in range(d["chc"]):
            rows.append({
                "facility_id":   f"{d['name'][:3].upper()}-CHC-{i+1:02d}",
                "facility_name": f"CHC {d['name']} {i+1}",
                "facility_type": "CHC",
                "district":      d["name"],
                "state":         STATE,
                "profile":       d["profile"],
                "latitude":      round(lat0 + rng.uniform(-0.22, 0.22), 5),
                "longitude":     round(lon0 + rng.uniform(-0.22, 0.22), 5),
                "catchment_population": int(CHC_POP * rng.uniform(0.80, 1.25)),
            })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 2. disease
def build_disease(facilities, start, days):
    """Weekly incidence per district, driven by seasonality and population."""
    dates = pd.date_range(start, periods=days // 7, freq="W-MON")
    pops = facilities.groupby("district")["catchment_population"].sum()

    rows = []
    for district, pop in pops.items():
        for dt in dates:
            month = dt.month - 1
            for disease, base in BASE_INCIDENCE.items():
                mult = SEASONALITY[disease][month]
                expected = base * mult * (pop / 100_000)
                cases = int(max(0, rng.poisson(expected) * rng.uniform(0.85, 1.15)))
                rows.append({
                    "district":   district,
                    "week_start": dt.date(),
                    "disease":    disease,
                    "case_count": cases,
                })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 3+4. ledger
def build_ledger(facilities, disease, start, days):
    """Convert cases -> consumption, simulate procurement, roll stock forward."""
    # district-week case lookup
    dw = {(r.district, r.week_start, r.disease): r.case_count
          for r in disease.itertuples()}

    weeks = sorted({r.week_start for r in disease.itertuples()})
    dist_pop = facilities.groupby("district")["catchment_population"].sum().to_dict()

    rows = []
    for f in facilities.itertuples():
        share = f.catchment_population / dist_pop[f.district]
        supply = PROFILE_SUPPLY[f.profile]

        for code, name, unit, disease_link, per_course, shelf in SKUS:
            # ---- daily demand series -------------------------------------
            demand = []
            for day_i in range(days):
                d = start + timedelta(days=day_i)
                wk = max([w for w in weeks if w <= d], default=weeks[0])
                cases = dw.get((f.district, wk, disease_link), 0)
                daily_cases = (cases * share) / 7.0
                # NFHS-5: not every case receives the medicine
                rate = NFHS_TREATMENT_RATE.get(code, 1.0)
                units = daily_cases * per_course * rate
                units *= rng.uniform(0.85, 1.15)          # noise
                demand.append(max(0.0, units))

            avg_daily = float(np.mean(demand)) or 1.0

            # ---- roll the ledger ----------------------------------------
            stock = avg_daily * 45 * supply["order_factor"]
            pipeline = {}          # arrival_day -> qty
            next_indent = 0

            for day_i in range(days):
                d = start + timedelta(days=day_i)
                opening = stock

                receipts = pipeline.pop(day_i, 0.0)
                stock += receipts

                issues = min(stock, demand[day_i])        # cannot issue what isn't there
                stock -= issues

                if day_i >= next_indent:
                    qty = avg_daily * INDENT_CYCLE_DAYS * supply["order_factor"]
                    lead = int(rng.integers(LEAD_TIME_MIN_DAYS, LEAD_TIME_MAX_DAYS + 1))
                    if rng.random() < supply["delay_prob"]:
                        lead += int(rng.integers(5, 15))   # delivery delay
                    arrive = day_i + lead
                    if arrive < days:
                        pipeline[arrive] = pipeline.get(arrive, 0.0) + qty
                    next_indent = day_i + INDENT_CYCLE_DAYS

                rows.append({
                    "facility_id":   f.facility_id,
                    "district":      f.district,
                    "sku_code":      code,
                    "sku_name":      name,
                    "date":          d,
                    "opening_stock": int(opening),
                    "receipts":      int(receipts),
                    "issues":        int(issues),
                    "closing_stock": int(stock),
                    "demand_true":   round(demand[day_i], 2),
                    "expiry_date":   d + timedelta(days=shelf),
                })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ main
def main():
    start = date.today() - timedelta(days=HISTORY_DAYS)

    print("1/3  building facilities ...")
    facilities = build_facilities()
    facilities.to_parquet(f"{OUT}/facilities.parquet", index=False)
    print(f"     {len(facilities)} facilities")

    print("2/3  building disease series ...")
    disease = build_disease(facilities, start, HISTORY_DAYS)
    disease.to_parquet(f"{OUT}/disease_weekly.parquet", index=False)
    print(f"     {len(disease):,} district-week-disease rows")

    print("3/3  building stock ledger (this takes ~1 min) ...")
    ledger = build_ledger(facilities, disease, start, HISTORY_DAYS)
    ledger.to_parquet(f"{OUT}/stock_ledger.parquet", index=False)
    print(f"     {len(ledger):,} ledger rows")

    stockouts = int((ledger["closing_stock"] == 0).sum())
    affected = ledger.loc[ledger["closing_stock"] == 0, "facility_id"].nunique()
    print(f"\nSTOCK-OUT DAYS: {stockouts:,} across {affected} facilities")
    print(f"Date range: {ledger['date'].min()} -> {ledger['date'].max()}")


if __name__ == "__main__":
    main()