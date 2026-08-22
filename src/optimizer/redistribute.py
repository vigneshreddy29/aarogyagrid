"""
AarogyaGrid — cross-district redistribution optimiser.

Min-cost flow via OR-Tools. Moves surplus to shortage subject to:
  - donor must retain its own reorder point
  - transfer distance under a ceiling
  - receiver need capped at its shortfall
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd
from math import radians, sin, cos, asin, sqrt
from ortools.linear_solver import pywraplp

from src.config import SKUS, MAX_TRANSFER_KM

OUT = "data/processed"
ROAD_FACTOR = 1.35        # road distance ≈ 1.35 x great-circle in rural India


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    a = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371 * 2 * asin(sqrt(a))


def solve_sku(alerts, code, name, per_course):
    sub = alerts[alerts.sku_code == code].copy()

    need = sub[sub.tier.isin(["CRITICAL", "STOCKOUT"])].copy()
    need["shortfall"] = (need["reorder_point"] - need["current_stock"]).clip(lower=1)

    donors = sub[sub.tier == "OK"].copy()
    donors["available"] = (donors["current_stock"] - donors["reorder_point"]).clip(lower=0)
    donors = donors[donors.available > 10]

    if need.empty or donors.empty:
        return []

    D = donors.reset_index(drop=True)
    N = need.reset_index(drop=True)

    dist = np.zeros((len(D), len(N)))
    for i, d in D.iterrows():
        for j, n in N.iterrows():
            dist[i, j] = haversine_km(d.latitude, d.longitude,
                                      n.latitude, n.longitude) * ROAD_FACTOR

    s = pywraplp.Solver.CreateSolver("SCIP")
    if not s:
        return []

    x = {}
    for i in range(len(D)):
        for j in range(len(N)):
            if dist[i, j] <= MAX_TRANSFER_KM:
                x[i, j] = s.IntVar(0, int(D.available[i]), f"x{i}_{j}")

    # donor cannot give away more than its surplus (reorder point protected)
    for i in range(len(D)):
        out = [x[i, j] for j in range(len(N)) if (i, j) in x]
        if out:
            s.Add(sum(out) <= int(D.available[i]))

    # receiver capped at its shortfall
    unmet = {}
    for j in range(len(N)):
        inc = [x[i, j] for i in range(len(D)) if (i, j) in x]
        unmet[j] = s.IntVar(0, int(N.shortfall[j]), f"u{j}")
        s.Add(sum(inc) + unmet[j] >= int(N.shortfall[j]))

    s.Minimize(
        1000 * sum(unmet.values())
        + sum(dist[i, j] * x[i, j] for (i, j) in x)
    )

    if s.Solve() != pywraplp.Solver.OPTIMAL:
        return []

    out = []
    for (i, j), var in x.items():
        q = int(var.solution_value())
        if q < 5:
            continue
        out.append({
            "sku_code": code, "sku_name": name, "quantity": q,
            "from_facility": D.facility_name[i], "from_district": D.district[i],
            "from_surplus_units": int(D.available[i]),
            "to_facility": N.facility_name[j], "to_district": N.district[j],
            "to_days_to_stockout": float(N.days_to_stockout[j]),
            "to_tier": N.tier[j],
            "road_km": round(dist[i, j], 1),
            "drive_min": int(dist[i, j] / 35 * 60),
            "courses_covered": round(q / per_course, 0),
            "cross_district": D.district[i] != N.district[j],
        })
    return out


def main():
    alerts = pd.read_parquet(f"{OUT}/alerts.parquet")
    per_course = {c: pc for c, _, _, _, pc, _ in SKUS}

    plans = []
    for code, name, _, _, pc, _ in SKUS:
        plans += solve_sku(alerts, code, name, pc)

    if not plans:
        print("no feasible transfers found")
        return

    df = pd.DataFrame(plans).sort_values("to_days_to_stockout")
    df.to_parquet(f"{OUT}/transfers.parquet", index=False)

    print(f"\n{len(df)} transfer orders generated")
    print(f"cross-district: {int(df.cross_district.sum())}")
    print(f"total units moved: {int(df.quantity.sum()):,}")
    print(f"treatment courses protected: {int(df.courses_covered.sum()):,}")
    print(f"mean distance: {df.road_km.mean():.1f} km")

    print("\n--- 5 most urgent transfer orders ---")
    for r in df.head(5).itertuples():
        print(f"\n  MOVE {r.quantity} x {r.sku_name}")
        print(f"    FROM {r.from_facility} ({r.from_district}) — {r.from_surplus_units} surplus")
        print(f"    TO   {r.to_facility} ({r.to_district}) — {r.to_days_to_stockout} days to stock-out")
        print(f"    {r.road_km} km, ~{r.drive_min} min | covers {int(r.courses_covered)} treatment courses")


if __name__ == "__main__":
    main()