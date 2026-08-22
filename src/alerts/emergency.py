"""
Emergency scenario simulation.

The challenge asks for early warning "during health emergencies". A steady-state
forecast cannot answer that: the question an officer actually has is "if dengue
doubles next week, which facilities fail first, and how fast?"

Each scenario applies a multiplier to specific disease-linked medicines, then
re-runs the days-to-stockout calculation. Nothing is retrained — the same
reorder-point arithmetic operates on elevated demand, which is exactly what
would happen in production.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd

OUT = "data/processed"

SCENARIOS = {
    "Dengue outbreak": {
        "note": "Vector-borne surge. Fever management and rehydration spike; "
                "platelet monitoring drives admissions. Modelled on IDSP "
                "post-monsoon dengue patterns in south India.",
        "multipliers": {"PAR001": 3.2, "ORS001": 2.1, "AMX001": 1.4},
        "footfall": 2.4,
        "onset_days": 7,
    },
    "Flood displacement": {
        "note": "Water contamination and displacement camps. Diarrhoeal and "
                "cholera caseload rises sharply within days of inundation.",
        "multipliers": {"ORS001": 4.1, "ZNC001": 3.8, "CIP001": 3.4, "PAR001": 1.6},
        "footfall": 2.9,
        "onset_days": 3,
    },
    "Heatwave": {
        "note": "Heat stress and dehydration. Chronic patients decompensate; "
                "ORS demand rises alongside cardiac and renal presentations.",
        "multipliers": {"ORS001": 2.6, "PAR001": 1.8, "MET001": 1.3},
        "footfall": 1.7,
        "onset_days": 2,
    },
    "Malaria surge": {
        "note": "Post-monsoon transmission peak. Antimalarial demand rises "
                "faster than any other class and substitutes poorly.",
        "multipliers": {"ACT001": 3.6, "PAR001": 2.0},
        "footfall": 1.9,
        "onset_days": 5,
    },
}

LEAD_TIME = 14


def simulate(alerts, name):
    """Re-run days-to-stockout under a scenario. Returns the modified frame."""
    s = SCENARIOS[name]
    df = alerts.copy()

    df["surge_mult"] = df["sku_code"].map(s["multipliers"]).fillna(1.0)
    df["surge_burn"] = df["daily_burn"] * df["surge_mult"]
    df["surge_days"] = df["current_stock"] / df["surge_burn"].clip(lower=0.01)

    def tier(r):
        if r.current_stock <= 0:            return "STOCKOUT"
        if r.surge_days < LEAD_TIME:        return "CRITICAL"
        if r.current_stock < r.reorder_point: return "WARNING"
        return "OK"

    df["surge_tier"] = df.apply(tier, axis=1)
    df["days_lost"] = (df["days_to_stockout"] - df["surge_days"]).round(1)
    return df


def main():
    alerts = pd.read_parquet(f"{OUT}/alerts.parquet")

    out = []
    for name, s in SCENARIOS.items():
        df = simulate(alerts, name)

        base_fail = int(alerts.tier.isin(["CRITICAL", "STOCKOUT"]).sum())
        surge_fail = int(df.surge_tier.isin(["CRITICAL", "STOCKOUT"]).sum())

        affected = df[df.surge_mult > 1]
        newly = df[(df.surge_tier == "CRITICAL") &
                   (~df.tier.isin(["CRITICAL", "STOCKOUT"]))]

        # facilities that fail before the next possible resupply
        within_onset = df[(df.surge_days <= s["onset_days"]) &
                          (df.current_stock > 0)]

        out.append({
            "scenario": name,
            "note": s["note"],
            "onset_days": s["onset_days"],
            "footfall_mult": s["footfall"],
            "baseline_at_risk": base_fail,
            "surge_at_risk": surge_fail,
            "newly_at_risk": len(newly),
            "fail_before_onset": len(within_onset),
            "median_days_lost": float(affected.days_lost.median()),
            "worst_facility": (df.loc[df.surge_days.idxmin(), "facility_name"]
                               if len(df) else None),
        })

        print(f"\n=== {name} ===")
        print(f"  {s['note']}")
        print(f"  at risk: {base_fail} -> {surge_fail}  "
              f"(+{surge_fail - base_fail}, {len(newly)} newly critical)")
        print(f"  median warning time lost: {affected.days_lost.median():.1f} days")
        print(f"  fail within {s['onset_days']}-day onset window: {len(within_onset)}")

        df.to_parquet(f"{OUT}/surge_{name.split()[0].lower()}.parquet", index=False)

    pd.DataFrame(out).to_json(f"{OUT}/scenarios.json", orient="records", indent=2)
    print(f"\nsaved -> {OUT}/scenarios.json + per-scenario parquet")


if __name__ == "__main__":
    main()