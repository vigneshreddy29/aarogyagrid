"""
PHC Resilience Score.

Combines supply, staffing, capacity and demand pressure into a single
0-100 operational vulnerability score per facility, so a district officer
can rank where to intervene rather than reading four separate tables.

Weights reflect operational impact: a facility with no medicine cannot
treat anyone, so supply dominates. Staffing and bed pressure determine
how well it copes with what it does have.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd

OUT = "data/processed"

WEIGHTS = {
    "supply":   0.40,   # medicine availability — cannot treat without it
    "urgency":  0.20,   # how soon the next stock-out lands
    "staffing": 0.20,   # people to dispense, refer, and raise indents
    "capacity": 0.20,   # bed headroom under patient load
}


def band(score):
    if score < 50:  return "HIGH RISK"
    if score < 70:  return "AT RISK"
    if score < 85:  return "STABLE"
    return "RESILIENT"


def main():
    alerts = pd.read_parquet(f"{OUT}/alerts.parquet")
    status = pd.read_parquet(f"{OUT}/facility_status.parquet")

    rows = []
    for f in status.itertuples():
        a = alerts[alerts.facility_id == f.facility_id]
        if a.empty:
            continue

        n = len(a)
        ok = int((a.tier == "OK").sum())
        out = int((a.tier == "STOCKOUT").sum())
        crit = int((a.tier == "CRITICAL").sum())

        # --- supply: share of the essential basket actually available ----
        supply = ok / n * 100

        # --- urgency: how close the nearest failure is -------------------
        at_risk = a[a.tier.isin(["CRITICAL", "STOCKOUT"])]
        if at_risk.empty:
            urgency = 100.0
            soonest = None
            driver = None
        else:
            soonest_row = at_risk.loc[at_risk.days_to_stockout.idxmin()]
            soonest = float(soonest_row.days_to_stockout)
            driver = soonest_row.sku_name
            urgency = float(np.clip(soonest / 14 * 100, 0, 100))

        # --- staffing ----------------------------------------------------
        staffing = float(f.staff_present_pct)

        # --- capacity: headroom, not occupancy ---------------------------
        capacity = float(np.clip(100 - f.occupancy_pct, 0, 100))
        capacity = min(100.0, capacity * 1.5)   # 33% free beds reads as healthy

        score = (WEIGHTS["supply"] * supply +
                 WEIGHTS["urgency"] * urgency +
                 WEIGHTS["staffing"] * staffing +
                 WEIGHTS["capacity"] * capacity)

        # the weakest dimension, for the explanation line
        parts = {"medicine availability": supply, "stock-out urgency": urgency,
                 "staff availability": staffing, "bed headroom": capacity}
        weakest = min(parts, key=parts.get)

        rows.append({
            "facility_id": f.facility_id,
            "facility_name": f.facility_name,
            "facility_type": f.facility_type,
            "district": f.district,
            "score": round(score),
            "band": band(score),
            "supply_pct": round(supply, 1),
            "urgency_pct": round(urgency, 1),
            "staffing_pct": round(staffing, 1),
            "capacity_pct": round(capacity, 1),
            "occupancy_pct": round(float(f.occupancy_pct), 1),
            "skus_stocked_out": out,
            "skus_critical": crit,
            "skus_total": n,
            "primary_risk": driver,
            "days_to_next_stockout": soonest,
            "weakest_factor": weakest,
        })

    df = pd.DataFrame(rows).sort_values("score")
    df.to_parquet(f"{OUT}/resilience.parquet", index=False)

    print("--- resilience bands ---")
    print(df.band.value_counts().to_string())

    print("\n--- 8 most vulnerable facilities ---")
    print(df[["facility_name", "district", "score", "band",
              "supply_pct", "staffing_pct", "primary_risk",
              "days_to_next_stockout"]].head(8).to_string(index=False))

    w = df.iloc[0]
    print(f"\nWORST: {w.facility_name} — {w.score}/100 ({w.band})")
    print(f"  primary risk: {w.primary_risk} in {w.days_to_next_stockout} days")
    print(f"  weakest factor: {w.weakest_factor}")
    print(f"  {w.skus_stocked_out} of {w.skus_total} medicines already at zero")

    print(f"\nsaved -> {OUT}/resilience.parquet")


if __name__ == "__main__":
    main()