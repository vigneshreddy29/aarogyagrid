"""
Generates causal alert briefs and Telugu translations, then caches them.

Cached to disk deliberately: the demo must never depend on a live API call.
"""
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
from src.gemini.client import ask

OUT = "data/processed"
CACHE = f"{OUT}/briefs.json"

SYSTEM = """You write supply alerts for Indian district health officers.

Output ONLY the alert. Never explain your reasoning or ask questions.

Exactly three sentences:
1. Which facility runs out of which medicine, in how many days.
2. WHY: cite the daily burn rate against the reorder point, and the
   monsoon season if the medicine treats a monsoon-driven illness
   (ORS, Zinc, Ciprofloxacin, Artemether-Lumefantrine).
3. The action: name the surplus facility and distance, or state that an
   emergency district indent is required.

Plain operational English. No bullets, no bold, no headings.
Never mention a trend multiplier."""


def build_prompt(a, transfer):
    src = (f"{transfer.from_facility}, {transfer.road_km} km away, "
           f"holding {transfer.from_surplus_units} surplus units"
           if transfer is not None else "no nearby surplus identified")

    return f"""Facility: {a.facility_name} ({a.facility_type}), {a.district} district
Medicine: {a.sku_name}
Stock on hand: {int(a.current_stock)} units
Consumption: {a.daily_burn} units/day
Depletion in: {a.days_to_stockout} days
Reorder point: {int(a.reorder_point)} units
Typical resupply lead time: 14 days
Population served: {int(a.catchment_population):,}
Nearest surplus: {src}
Season: August, peak monsoon in Telangana"""


def main():
    alerts = pd.read_parquet(f"{OUT}/alerts.parquet")
    transfers = pd.read_parquet(f"{OUT}/transfers.parquet")

    # Lead with preventable cases — that is the product story.
    prev = (alerts[(alerts.tier == "CRITICAL") & (alerts.days_to_stockout >= 3)]
            .sort_values("days_to_stockout", ascending=False).head(12))
    already = (alerts[alerts.tier == "STOCKOUT"]
               .sort_values("daily_burn", ascending=False).head(8))
    urgent = pd.concat([prev, already])

    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))

    for i, a in enumerate(urgent.itertuples(), 1):
        key = f"{a.facility_id}|{a.sku_code}"
        if key in cache:
            print(f"[{i}/{len(urgent)}] cached — {a.facility_name}")
            continue

        match = transfers[(transfers.to_facility == a.facility_name) &
                          (transfers.sku_code == a.sku_code)]
        t = match.iloc[0] if len(match) else None

        prompt = build_prompt(a, t)
        english = ask(prompt, system=SYSTEM)
        if not english:
            print(f"[{i}] FAILED — {a.facility_name}")
            continue

        telugu = ask(
            f"Translate to Telugu for a PHC pharmacist. "
            f"Keep medicine names in English. Return only the translation:\n\n{english}",
            temperature=0.1)

        cache[key] = {
            "facility": a.facility_name,
            "sku": a.sku_name,
            "district": a.district,
            "days_to_stockout": float(a.days_to_stockout),
            "english": english,
            "telugu": telugu or "",
        }
        print(f"[{i}/{len(urgent)}] {a.facility_name} — {a.sku_name}")

    json.dump(cache, open(CACHE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"\n{len(cache)} briefs cached -> {CACHE}")
    if cache:
        first = list(cache.values())[0]
        print(f"\n--- sample ---\n{first['english']}\n\n{first['telugu']}")


if __name__ == "__main__":
    main()