# AarogyaGrid

**Predictive stock-out prevention for India's primary health network.**

DVDMS records what happened. AarogyaGrid predicts what's about to happen, and tells districts what to do about it — without any state sharing its raw data.

**Live demo:** https://aarogyagrid-bwai.streamlit.app/

Built for *Build with AI: Code for Communities* — Track 3, Smart Health & Supply Chain Resilience.

---

## The problem

Essential medicine availability across major Indian states runs between **17% and 51%**, and stock-outs last **4 to 14 weeks** — not days. In one two-state survey, 60% of unavailable medicines had been out of stock for three to six months.

The consequence is financial as well as clinical: roughly **48% of Indian healthcare spending is out-of-pocket**, and medication accounts for about 70% of that. When a PHC has no stock, the patient pays privately or goes without.

The structural cause is visible in how the system works. Stock flows downward on a **request-and-indent basis** — a pharmacist notices he is low, raises an indent, and waits 7 to 21 days. Nothing in the chain anticipates demand. It only reacts to depletion, by which point the shelf is often already empty.

## What already exists, and what it doesn't do

India already runs **DVDMS (e-Aushadhi)**, a C-DAC-built supply chain system deployed across most states. It handles procurement, inventory, and distribution down to PHC level.

It is a transactional ledger. Three gaps remain:

1. **It records, it doesn't predict.** It reports current stock and last month's consumption. It cannot tell you that you will run out in eleven days.
2. **It is state-siloed.** Every state runs its own instance. Telangana's warehouse cannot see Andhra Pradesh's surplus.
3. **Disease signals and stock are disconnected.** DVDMS knows inventory. IDSP knows outbreaks. They never speak.

**AarogyaGrid is not a replacement for DVDMS. It is the intelligence layer above it.**

## What it does

| Layer | Function |
|---|---|
| **Ingestion** | Open API accepting DVDMS-shaped stock records — a state points its existing export at an endpoint |
| **Forecasting** | Ridge regression per SKU, using disease surveillance as a predictive feature |
| **Early warning** | Days-to-stock-out, reorder points, safety stock — standard inventory theory, five alert tiers |
| **Redistribution** | OR-Tools min-cost flow producing executable transfer orders between facilities |
| **Federation** | States share model coefficients, never raw data |
| **Gemini** | Causal alert briefs in English and Telugu, explaining *why* each stock-out is coming |

## Results

**Forecasting** — Ridge beats a seasonal-naive baseline on all 8 SKUs:

| SKU | Ridge MAPE | Baseline | Improvement |
|---|---|---|---|
| Artemether-Lumefantrine | 12.81% | 16.85% | **24.0%** |
| Ciprofloxacin 500mg | 17.95% | 22.82% | **21.3%** |
| ORS Sachet | 12.42% | 15.35% | **19.1%** |
| Zinc Sulphate 20mg | 14.57% | 17.19% | 15.2% |
| Paracetamol 500mg | 13.57% | 15.66% | 13.3% |
| Metformin 500mg | 11.47% | 13.22% | 13.2% |
| Iron Folic Acid | 11.95% | 13.72% | 12.9% |
| Amoxicillin 500mg | 15.03% | 17.24% | 12.8% |

The largest gains fall on the **outbreak-driven medicines** — antimalarials, cholera antibiotics, ORS. That is the disease surveillance feature doing real predictive work, not a coincidence.

**Alerts** — across 37 facilities and 8 SKUs: 23 facility-SKU pairs already at zero, 52 preventable stock-outs identified with a **median 5.7 days of warning** (17 alerts with 7–14 days).

**Redistribution** — 50 transfer orders, 38 of them cross-district, moving 41,692 units and protecting an estimated 1,917 treatment courses at a mean distance of 44.6 km.

**Federation** — three simulated state nodes with deliberately unequal data:

| Node | Training rows | Alone | Federated | Gain |
|---|---|---|---|---|
| Telangana (data-rich) | 6,780 | 10.21% | 10.20% | +0.1% |
| Odisha (moderate) | 2,532 | 12.04% | 11.02% | **+8.4%** |
| Meghalaya (data-poor) | 310 | 23.49% | 20.85% | **+11.2%** |

The gain scales inversely with local data volume. A state with three months of history cannot learn monsoon seasonality alone — but seasonality is *shared structure*, so it can be learned collectively. **12 coefficients and 12 feature statistics cross the boundary. No inventory row ever does.**

## Data provenance

Live PHC inventory APIs are not publicly available in India. This is stated plainly rather than obscured.

| Data | Source | Real or derived |
|---|---|---|
| District structure, PHC/CHC counts | Real Telangana districts, Indian PHC norms (1 PHC per ~30,000 population) | **Real** |
| SKU list | National List of Essential Medicines (NLEM) | **Real** |
| Disease seasonality | Modelled on published IDSP seasonal patterns for south Indian districts | **Real basis** |
| Clinical consumption rates | Standard treatment courses (ORS 6 sachets/course, ACT 1 course, etc.) | **Real** |
| Stock levels, receipts, issues | **Derived** from the above via documented clinical norms | **Synthesised** |
| Road distances | Haversine × 1.35 rural road factor | **Derived** |

**Consumption is never invented.** It is computed from disease incidence through clinical treatment norms. The result: ORS consumption correlates with district diarrhoeal cases at **r = 0.960** — visible on the "Why It Works" tab.

The generator is open source in `src/generator/`. The ingestion API (`docs/openapi.yaml`) is the interface a real state connects to replace synthesised data with live DVDMS records.

## Google AI integration

Gemini performs work that is not reducible to a template:

- **Causal explanation** — each alert becomes a three-sentence brief naming *why* depletion is happening, connecting burn rate, reorder point, and monsoon disease risk
- **Multilingual delivery** — English for the district officer, Telugu for the PHC pharmacist, medicine names preserved in English
- **Model fallback chain** — requests fall through a preference list of Gemini models, so retirement or overload degrades gracefully rather than failing
- **Cached output** — briefs are generated ahead of time and cached, so the live demo never depends on an API call

Example, unedited:

> *PHC Yadadri Bhuvanagiri 7 will run out of Artemether-Lumefantrine in 13 days. The current stock has fallen below the reorder point of 210 units due to a daily burn rate of 13.49 units, which is exacerbated by the high malaria risk during the peak monsoon season. An emergency district indent is required immediately to replenish supplies.*

## Architecture

```
  DVDMS / e-Aushadhi export
            |
            v
  [ Ingestion API ]  docs/openapi.yaml — open schema, DVDMS-shaped
            |
            v
  [ Forecasting ]    Ridge per SKU + IDSP disease features
            |
            v
  [ Early warning ]  days-to-stockout, reorder point, safety stock
            |
            +---> [ Redistribution ]  OR-Tools min-cost flow
            |
            +---> [ Gemini briefs ]   causal explanation, EN + TE
            |
            v
  [ Federation ]     coefficients only, across state nodes
```

## Running it

```bash
git clone https://github.com/vigneshreddy29/aarogyagrid.git
cd aarogyagrid
pip install -r requirements.txt

# Gemini key (free, from https://aistudio.google.com/apikey)
echo "GEMINI_API_KEY=your_key" > .env

python src/generator/build_data.py      # build the data foundation
python src/forecast/train.py            # train forecasters
python src/alerts/engine.py             # compute alerts
python src/optimizer/redistribute.py    # solve redistribution
python src/federated/fedavg.py          # run federation
python src/gemini/briefs.py             # generate briefs

python -m streamlit run app.py
```

## Deployment path

**District → State → National.** The system requires no new hardware and no new data collection. A state connects its existing DVDMS export to the ingestion API and receives forecasts, alerts, and transfer recommendations against data it already holds.

**Cross-border.** The inputs are facility, item, stock level, consumption rate, and distance — nothing India-specific. Brazil and South Africa operate comparable primary health networks with the same stock-out problem and the same data-sovereignty constraints that federation is designed to respect.

## Stack

Python · scikit-learn · Google OR-Tools · Gemini API · Streamlit · Plotly · Parquet
