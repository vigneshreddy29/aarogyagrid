"""
AarogyaGrid — stock-out early warning.

Converts forecasts into actionable alerts using standard inventory theory:
  reorder point = (lead time x daily demand) + safety stock
  safety stock  = Z x sigma x sqrt(lead time)
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd
import pickle

from src.config import SKUS, SERVICE_LEVEL_Z, LEAD_TIME_MAX_DAYS
from src.forecast.train import FEATURES

OUT = "data/processed"
LEAD_TIME = 14          # planning assumption: mean lead time


def main():
    feats = pd.read_parquet(f"{OUT}/features.parquet")
    facs  = pd.read_parquet(f"{OUT}/facilities.parquet")
    with open("models/forecast_models.pkl", "rb") as f:
        models = pickle.load(f)

    # latest observation per facility-SKU = "today"
    latest = (feats.sort_values("date")
                   .groupby(["facility_id", "sku_code"], as_index=False)
                   .tail(1)
                   .dropna(subset=FEATURES))

    sku_name = {c: n for c, n, *_ in SKUS}
    rows = []

    for code, m in models.items():
        sub = latest[latest.sku_code == code]
        if sub.empty:
            continue

        X = m["scaler"].transform(sub[FEATURES])
        daily = np.maximum(0.1, m["model"].predict(X))
        sigma = max(m["resid_std"], 0.1)

        safety  = float(SERVICE_LEVEL_Z * sigma * np.sqrt(LEAD_TIME))
        reorder = (LEAD_TIME * daily) + safety
        stock   = sub["closing_stock"].values
        dts     = stock / daily                      # days to stock-out

        for i, r in enumerate(sub.itertuples()):
            if stock[i] <= 0:                 tier = "STOCKOUT"
            elif dts[i] < LEAD_TIME:          tier = "CRITICAL"
            elif stock[i] < reorder[i]:       tier = "WARNING"
            elif stock[i] < reorder[i] * 1.5: tier = "WATCH"
            else:                             tier = "OK"

            rows.append({
                "facility_id":      r.facility_id,
                "district":         r.district,
                "sku_code":         code,
                "sku_name":         sku_name[code],
                "current_stock":    int(stock[i]),
                "daily_burn":       round(float(daily[i]), 2),
                "days_to_stockout": round(float(dts[i]), 1),
                "reorder_point":    int(reorder[i]),
                "safety_stock":     int(safety),
                "tier":             tier,
                "disease_trend":    round(float(r.disease_trend), 2),
                "as_of":            r.date,
            })

    alerts = pd.DataFrame(rows).merge(
        facs[["facility_id", "facility_name", "facility_type",
              "latitude", "longitude", "catchment_population"]],
        on="facility_id", how="left")

    # a facility burning <1 unit/day is not an operationally meaningful alert
    alerts.loc[(alerts.daily_burn < 1.0) & (alerts.tier.isin(["CRITICAL", "STOCKOUT"])),
               "tier"] = "WATCH"

    print("\n--- alerts by tier ---")
    print(alerts["tier"].value_counts().to_string())

    print("\n--- CRITICAL by district ---")
    crit = alerts[alerts.tier == "CRITICAL"]
    print(crit.groupby("district").size().to_string() if len(crit) else "  none")

    cols = ["facility_name", "sku_name", "current_stock", "daily_burn",
            "days_to_stockout", "tier"]

    print("\n--- ALREADY STOCKED OUT (the cost of no early warning) ---")
    so = alerts[alerts.tier == "STOCKOUT"]
    print(f"  {len(so)} facility-SKU pairs currently at zero")

    c = alerts[alerts.tier == "CRITICAL"]["days_to_stockout"]
    print(f"\n--- warning lead time across {len(c)} CRITICAL alerts ---")
    print(f"  median {c.median():.1f} d | 0-3d: {(c<=3).sum()} | "
          f"3-7d: {((c>3)&(c<=7)).sum()} | 7-14d: {(c>7).sum()}")
    prev = alerts[alerts.tier == "CRITICAL"].nsmallest(10, "days_to_stockout")
    print(prev[cols].to_string(index=False) if len(prev) else "  none")

    print(f"\nsaved {len(alerts):,} alert rows -> {OUT}/alerts.parquet")


if __name__ == "__main__":
    main()