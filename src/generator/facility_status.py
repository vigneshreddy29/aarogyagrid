"""
Bed occupancy and staff attendance per facility.

The problem statement asks for visibility into beds and personnel alongside
medicine stock. No public API exposes either in real time, so this module
demonstrates the ingestion schema those fields would arrive through —
generated against real IHIP/HMIS structural norms, clearly labelled as such
in the interface.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd
from src.config import RANDOM_SEED, PROFILE_SUPPLY

rng = np.random.default_rng(RANDOM_SEED + 7)
OUT = "data/processed"

# Indian Public Health Standards (IPHS) staffing and bed norms
NORMS = {
    "PHC": {"beds": 6,  "doctors": 2, "nurses": 4, "pharmacists": 1},
    "CHC": {"beds": 30, "doctors": 6, "nurses": 14, "pharmacists": 2},
}


def main():
    fac = pd.read_parquet(f"{OUT}/facilities.parquet")
    alerts = pd.read_parquet(f"{OUT}/alerts.parquet")

    # facilities under supply stress tend to be under strain generally
    stress = (alerts[alerts.tier.isin(["STOCKOUT", "CRITICAL"])]
              .groupby("facility_id").size().rename("stressed_skus"))

    rows = []
    for f in fac.itertuples():
        n = NORMS[f.facility_type]
        s = int(stress.get(f.facility_id, 0))
        load = min(1.0, 0.55 + 0.06 * s)          # occupancy rises with stress

        occupied = int(np.clip(rng.normal(n["beds"] * load, 1.2), 0, n["beds"]))

        # sanctioned vs present — vacancy is the chronic Indian PHC problem
        vac = PROFILE_SUPPLY[f.profile]["delay_prob"]
        doc_present = int(np.clip(rng.binomial(n["doctors"], 1 - vac), 0, n["doctors"]))
        nur_present = int(np.clip(rng.binomial(n["nurses"], 1 - vac * 0.7), 0, n["nurses"]))
        phm_present = int(np.clip(rng.binomial(n["pharmacists"], 1 - vac), 0, n["pharmacists"]))

        rows.append({
            "facility_id": f.facility_id,
            "facility_name": f.facility_name,
            "facility_type": f.facility_type,
            "district": f.district,
            "beds_sanctioned": n["beds"],
            "beds_occupied": occupied,
            "occupancy_pct": round(occupied / n["beds"] * 100, 1),
            "doctors_sanctioned": n["doctors"],
            "doctors_present": doc_present,
            "nurses_sanctioned": n["nurses"],
            "nurses_present": nur_present,
            "pharmacists_sanctioned": n["pharmacists"],
            "pharmacists_present": phm_present,
            "staff_present_pct": round(
                (doc_present + nur_present + phm_present) /
                (n["doctors"] + n["nurses"] + n["pharmacists"]) * 100, 1),
            "supply_stressed_skus": s,
        })

    df = pd.DataFrame(rows)
    df.to_parquet(f"{OUT}/facility_status.parquet", index=False)

    print(f"{len(df)} facilities")
    print(f"mean bed occupancy: {df.occupancy_pct.mean():.1f}%")
    print(f"mean staff present: {df.staff_present_pct.mean():.1f}%")
    print(f"facilities above 85% occupancy: {(df.occupancy_pct > 85).sum()}")
    print(f"facilities below 70% staffed:   {(df.staff_present_pct < 70).sum()}")
    print(f"\nsaved -> {OUT}/facility_status.parquet")


if __name__ == "__main__":
    main()