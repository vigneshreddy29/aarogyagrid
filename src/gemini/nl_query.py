"""
Natural-language querying over facility data.

Gemini translates an officer's plain-English question into a pandas
filter expression, which is validated and executed against the alert
and capacity tables. This is Google AI on the INPUT side of the system:
it does work no template could do, on data it has never seen.
"""

import sys, os, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
from src.gemini.client import ask

SCHEMA = """You translate questions about Indian PHC medicine supply into a
single pandas query() expression.

The dataframe `df` has these columns:
  facility_name        str    e.g. "PHC Yadadri Bhuvanagiri 6"
  facility_type        str    "PHC" or "CHC"
  district             str    "Nalgonda" | "Yadadri Bhuvanagiri" | "Suryapet"
  sku_name             str    "ORS Sachet (WHO formula)" | "Zinc Sulphate 20mg"
                              | "Paracetamol 500mg" | "Artemether-Lumefantrine"
                              | "Ciprofloxacin 500mg" | "Iron Folic Acid"
                              | "Amoxicillin 500mg" | "Metformin 500mg"
  current_stock        int    units on hand
  daily_burn           float  units consumed per day
  days_to_stockout     float  days until depletion
  reorder_point        int    threshold for reordering
  tier                 str    "STOCKOUT" | "CRITICAL" | "WARNING" | "WATCH" | "OK"
  occupancy_pct        float  bed occupancy percentage
  staff_present_pct    float  staff present as % of sanctioned
  catchment_population int

Domain notes:
  - "antimalarial" -> Artemether-Lumefantrine
  - "ORS" / "rehydration" -> ORS Sachet (WHO formula)
  - "antibiotic" -> Ciprofloxacin 500mg or Amoxicillin 500mg
  - "understaffed" -> staff_present_pct < 70
  - "full" / "at capacity" -> occupancy_pct > 85
  - "running out" / "at risk" -> tier in ["CRITICAL","STOCKOUT"]
  - "already out" -> tier == "STOCKOUT"

Return ONLY the query expression. No markdown, no backticks, no explanation,
no assignment. Use str.contains for partial name matches.

Examples:
Q: which facilities are already out of ORS?
A: tier == "STOCKOUT" and sku_name.str.contains("ORS")

Q: understaffed facilities in Yadadri running out of antimalarials
A: district == "Yadadri Bhuvanagiri" and staff_present_pct < 70 and sku_name.str.contains("Artemether") and tier in ["CRITICAL","STOCKOUT"]

Q: CHCs with more than 7 days of warning
A: facility_type == "CHC" and days_to_stockout > 7 and tier == "CRITICAL"
"""

# Anything that could mutate state or reach outside the dataframe.
BLOCKED = re.compile(
    r"\b(import|exec|eval|open|__|os\.|sys\.|drop|delete|to_csv|to_parquet)\b",
    re.IGNORECASE)


def build_frame():
    """Alerts joined with facility capacity — the queryable view."""
    OUT = "data/processed"
    a = pd.read_parquet(f"{OUT}/alerts.parquet")
    s = pd.read_parquet(f"{OUT}/facility_status.parquet")
    return a.merge(
        s[["facility_id", "occupancy_pct", "staff_present_pct",
           "beds_occupied", "beds_sanctioned"]],
        on="facility_id", how="left")


def to_query(question):
    """Ask Gemini for a pandas query expression."""
    expr = ask(f"Q: {question}\nA:", system=SCHEMA, temperature=0.0)
    if not expr:
        return None, "Gemini unavailable"

    expr = expr.strip().strip("`").replace("```", "").strip()
    if expr.lower().startswith("a:"):
        expr = expr[2:].strip()

    if BLOCKED.search(expr):
        return None, "Query rejected: contains a disallowed operation"
    if len(expr) > 500:
        return None, "Query rejected: expression too long"

    return expr, None


def run(question, df=None):
    """Returns (result_df, expression, error)."""
    if df is None:
        df = build_frame()

    expr, err = to_query(question)
    if err:
        return None, expr, err

    try:
        return df.query(expr, engine="python"), expr, None
    except Exception as e:
        return None, expr, f"Could not execute: {type(e).__name__}: {e}"


if __name__ == "__main__":
    tests = [
        "which facilities are already out of ORS?",
        "understaffed facilities in Yadadri running out of antimalarials",
        "CHCs with more than 7 days of warning",
        "facilities at bed capacity that are also running out of medicine",
    ]
    frame = build_frame()
    for q in tests:
        res, expr, err = run(q, frame)
        print("=" * 70)
        print(f"Q: {q}")
        print(f"→ {expr}")
        if err:
            print(f"  ERROR: {err}")
        else:
            print(f"  {len(res)} rows")
            if len(res):
                print(res[["facility_name", "sku_name", "days_to_stockout",
                           "tier"]].head(4).to_string(index=False))