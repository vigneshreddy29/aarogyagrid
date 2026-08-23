"""
Natural-language querying over facility data.

Gemini translates an officer's plain-English question into a pandas
filter expression, which is validated and executed against the alert
and capacity tables, then summarises the result as an actionable brief.

This is Google AI on the INPUT side of the system: it does work no
template could do, on data it has never seen.
"""

import sys, os, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
from src.gemini.client import ask

OUT = "data/processed"


# ---------------------------------------------------------------- prompts

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
  - "antibiotic" / "antibiotics" -> Ciprofloxacin 500mg or Amoxicillin 500mg
  - "understaffed" -> staff_present_pct < 70
  - "full" / "at capacity" -> occupancy_pct > 85
  - "running out" / "at risk" -> tier in ["CRITICAL","STOCKOUT"]
  - "already out" / "exhausted" -> tier == "STOCKOUT"
  - "days of warning" / "warning time" / "lead time" -> days_to_stockout,
    combined with tier == "CRITICAL"
  - the user may misspell terms; interpret intent generously

Return ONLY the query expression. No markdown, no backticks, no explanation,
no assignment. Use str.contains for partial name matches.
If the question is NOT a request to filter facility or medicine data — for
example a question about the interface, a greeting, a request to explain
something, or anything unrelated — return exactly this and nothing else:
OUT_OF_SCOPE

Examples:
Q: which facilities are already out of ORS?
A: tier == "STOCKOUT" and sku_name.str.contains("ORS")

Q: understaffed facilities in Yadadri running out of antimalarials
A: district == "Yadadri Bhuvanagiri" and staff_present_pct < 70 and sku_name.str.contains("Artemether") and tier in ["CRITICAL","STOCKOUT"]

Q: CHCs with more than 7 days of warning
A: facility_type == "CHC" and days_to_stockout > 7 and tier == "CRITICAL"

Q: facilities at bed capacity that are also running out of medicine
A: occupancy_pct > 85 and tier in ["CRITICAL","STOCKOUT"]
"""


SUMMARY_SYSTEM = """You brief an Indian district health officer on query results.

Write 2-3 sentences, plain operational English:
1. What the results show — count, and the pattern across them.
2. The most urgent case, named specifically with its number.
3. What the officer should do next.

No preamble, no bullets, no bold. If nothing matches, say so in one sentence.

Use the correct clinical terms from the results, not the user's wording — if
they misspelled something, silently use the right term."""


# Anything that could mutate state or reach outside the dataframe.
BLOCKED = re.compile(
    r"\b(import|exec|eval|open|__|os\.|sys\.|drop|delete|to_csv|to_parquet)\b",
    re.IGNORECASE)


# ---------------------------------------------------------------- data

def build_frame():
    """Alerts joined with facility capacity — the queryable view."""
    a = pd.read_parquet(f"{OUT}/alerts.parquet")
    s = pd.read_parquet(f"{OUT}/facility_status.parquet")
    return a.merge(
        s[["facility_id", "occupancy_pct", "staff_present_pct",
           "beds_occupied", "beds_sanctioned"]],
        on="facility_id", how="left")


# ---------------------------------------------------------------- query

def to_query(question):
    """Ask Gemini for a pandas query expression. Returns (expr, error)."""
    expr = ask(f"Q: {question}\nA:", system=SCHEMA, temperature=0.0)
    if not expr:
        return None, "Gemini unavailable — check the API key"

    expr = expr.strip().strip("`").replace("```", "").strip()
    if expr.lower().startswith("a:"):
        expr = expr[2:].strip()
    if expr.strip().upper() == "OUT_OF_SCOPE":
        return None, ("That question isn't a data filter. Try asking about "
                      "facilities, medicines or stock — for example "
                      "*which CHCs are running out of antibiotics?*")    

    if BLOCKED.search(expr):
        return None, "Query rejected: contains a disallowed operation"
    if len(expr) > 500:
        return None, "Query rejected: expression too long"

    return expr, None


def run(question, df=None):
    """Execute a natural-language question. Returns (result_df, expr, error)."""
    if df is None:
        df = build_frame()

    expr, err = to_query(question)
    if err:
        return None, expr, err

    try:
        res = df.query(expr, engine="python")
    except Exception as e:
        return None, expr, f"Could not execute: {type(e).__name__}: {e}"

    if len(res) > len(df) * 0.9:
        return None, expr, ("That matched almost every record — the question "
                            "was probably too broad. Try narrowing it to a "
                            "district, medicine or alert status.")
    return res, expr, None

# ---------------------------------------------------------------- summary

def summarise(question, res):
    """Turn query results into an actionable brief."""
    if res is None or len(res) == 0:
        return "No facilities match that query."

    cols = ["facility_name", "facility_type", "district", "sku_name",
            "current_stock", "daily_burn", "days_to_stockout", "tier"]
    have = [c for c in cols if c in res.columns]
    sample = res.sort_values("days_to_stockout")[have].head(12)

    prompt = (f"Question asked: {question}\n"
              f"Total matches: {len(res)}\n"
              f"Already at zero: {int((res.tier == 'STOCKOUT').sum())}\n\n"
              f"Results:\n{sample.to_string(index=False)}")

    return ask(prompt, system=SUMMARY_SYSTEM, temperature=0.3) or ""


# ---------------------------------------------------------------- test

if __name__ == "__main__":
    tests = [
        "which facilities are already out of ORS?",
        "understaffed facilities in Yadadri running out of antimalarials",
        "CHCs with more than 7 days of warning",
        "Which CHS Are Running For Antibodies",
    ]

    frame = build_frame()
    for q in tests:
        res, expr, err = run(q, frame)
        print("=" * 72)
        print(f"Q: {q}")
        print(f"→ {expr}")
        if err:
            print(f"  ERROR: {err}")
            continue

        print(f"  {len(res)} rows")
        if len(res):
            print(res[["facility_name", "sku_name", "days_to_stockout",
                       "tier"]].head(4).to_string(index=False))
            print(f"\n  BRIEF: {summarise(q, res)}")
# ==================================================================== router

ROUTER = """Classify the user's question into exactly one word:

FILTER  - asks for specific facilities, medicines, or stock records that
          match conditions. "which CHCs are out of antibiotics",
          "understaffed facilities in Yadadri"
ADVISE  - asks what should be done, why a facility or district is
          struggling, what the priority is, how to fix or reduce a
          problem, or for a recommendation or diagnosis grounded in
          the current situation. "what should the district do",
          "why is Yadadri failing", "where should we act first",
          "how do we stop stockouts"
EXPLAIN - asks how the SYSTEM works — the model, the maths, the data
          sources, or what a term means. Not about any specific facility
          or district. "how does the forecast work", "what is a
          resilience index", "where does the data come from"
OTHER   - anything else: greetings, unrelated topics, chit-chat

Return only the single word."""


ADVISE_SYSTEM = """You are briefing an Indian district health officer on their
own supply situation. You have their live figures. Write the briefing.

Write three short paragraphs — no headings, no bullet points, no labels.
Keep the whole briefing under 150 words:

First, the situation — how many facilities are affected, what is already at
zero, what is about to be.

Second, the pattern — which district or facilities carry the burden, which
medicines dominate, and whether staffing or bed pressure compounds it.

Third, the action — the specific transfers or emergency indents to authorise
this week, naming facilities and medicines from the data, and the one
structural change that would stop it recurring.



Use only the figures provided. Name real facilities and medicines from the
data. Never restate these instructions, never list your constraints, never
use asterisks or numbered points. Write as one continuous briefing an
officer would read aloud in a meeting."""


EXPLAIN_FACTS = """AarogyaGrid facts — answer only from these:

FORECASTING: Ridge regression per medicine, using lagged IDSP disease
surveillance (previous week, two weeks back, 4-week mean) plus consumption
history and calendar seasonality. Features are point-in-time correct — no
same-week disease count enters the model, because IDSP publishes weekly in
arrears. Compared against three baselines: naive persistence, 7-day moving
average, seasonal naive. Ridge wins on 6 of 8 medicines; the other two fall
back to naive because sparse outbreak-driven demand defeats regression.

ALERTS: days_to_stockout = current stock / forecast daily burn. Reorder point
= (lead time x daily demand) + safety stock, where safety stock =
1.65 x demand std dev x sqrt(lead time), a 95% service level. Five tiers:
STOCKOUT, CRITICAL, WARNING, WATCH, OK.

REDISTRIBUTION: OR-Tools min-cost flow. Minimises unmet demand, then transport
distance, then expiry waste. Donors must retain their own reorder point.
Distance capped at 75 km. Every order requires human approval.

FEDERATION: each node trains locally; only model coefficients and feature
statistics are exchanged. No inventory or patient record crosses a boundary.
Data-poor nodes gain most (25% error reduction on a 3-month node); data-rich
nodes are essentially unaffected.

RESILIENCE INDEX: medicine availability 40%, stock-out urgency 20%, staff
availability 20%, bed headroom 20%. A prototype policy index, not validated.

DATA: facility locations are real Telangana mandal headquarters. Disease
incidence and treatment rates come from NFHS-5 Telangana. Seasonality is
calibrated against 218 IDSP outbreak reports via the EpiClim dataset.
Stock levels, footfall, beds and staffing are synthesised from those real
anchors — no public API exposes live PHC inventory in India.

Answer in 2-3 sentences. If the question is outside these facts, say the
system does not cover it."""


def route(question):
    r = ask(f"Question: {question}", system=ROUTER, temperature=0.0)
    r = (r or "OTHER").strip().upper()
    return r if r in {"FILTER", "ADVISE", "EXPLAIN", "OTHER"} else "OTHER"


def situation(alerts, resil, transfers, status, scen=None):
    """Compact snapshot of the live situation, for grounding advice."""
    worst = resil.head(6)[["facility_name", "district", "score", "band",
                           "primary_risk", "days_to_next_stockout",
                           "supply_pct", "staffing_pct"]]
    urgent = (alerts[alerts.tier.isin(["CRITICAL", "STOCKOUT"])]
              .nsmallest(10, "days_to_stockout")
              [["facility_name", "sku_name", "current_stock",
                "daily_burn", "days_to_stockout", "tier"]])
    moves = transfers.head(6)[["from_facility", "to_facility", "sku_name",
                               "quantity", "road_km", "courses_covered"]]

    txt = f"""CURRENT SITUATION — {alerts.facility_id.nunique()} facilities, Telangana

Alert counts: {alerts.tier.value_counts().to_dict()}
Already at zero: {int((alerts.tier == 'STOCKOUT').sum())} facility-medicine pairs
Preventable: {int((alerts.tier == 'CRITICAL').sum())}, median warning \
{alerts[alerts.tier == 'CRITICAL'].days_to_stockout.median():.1f} days
High-risk facilities: {int((resil.band == 'HIGH RISK').sum())} of {len(resil)}
Mean staff present: {status.staff_present_pct.mean():.0f}% of sanctioned
Mean bed occupancy: {status.occupancy_pct.mean():.0f}%

MOST VULNERABLE FACILITIES
{worst.to_string(index=False)}

MOST URGENT MEDICINES
{urgent.to_string(index=False)}

AVAILABLE TRANSFERS ({len(transfers)} total, \
{int(transfers.courses_covered.sum()):,} courses protected)
{moves.to_string(index=False)}"""

    if scen:
        s = pd.DataFrame(scen)
        txt += f"\n\nEMERGENCY SCENARIOS (modelled)\n{s[['scenario','surge_at_risk','newly_at_risk','median_days_lost']].to_string(index=False)}"
    return txt


def advise(question, ctx):
    return ask(f"{ctx}\n\nOfficer's question: {question}",
               system=ADVISE_SYSTEM, temperature=0.4) or ""


def explain(question):
    return ask(f"Question: {question}", system=EXPLAIN_FACTS,
               temperature=0.2) or ""