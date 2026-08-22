<div align="center">

# 🏥 AarogyaGrid

### Predictive stock-out prevention for India's primary health network

*DVDMS records what happened. AarogyaGrid predicts what's about to happen —<br>and tells districts what to do about it, without any state sharing its raw data.*

<br>

[![Live Demo](https://img.shields.io/badge/▶_Live_Demo-Open_App-FF4B4B?style=for-the-badge)](https://aarogyagrid-bwai.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/Google_Gemini-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)

![Status](https://img.shields.io/badge/status-working_prototype-success)
![Coverage](https://img.shields.io/badge/prototype_coverage-Telangana%3A_3_districts-informational)
![Track](https://img.shields.io/badge/track-Smart_Health_%26_Supply_Chain-orange)

<br>

**Build with AI: Code for Communities** · Track 3 — Smart Health & Supply Chain Resilience

</div>

---

<div align="center">

### 🩺 The numbers that matter

| **17–51%** | **4–14 weeks** | **70%** |
|:---:|:---:|:---:|
| Essential medicine availability<br>across major Indian states | How long a stock-out lasts<br>— not days, *weeks* | Share of out-of-pocket health<br>spending that goes to medicines |

</div>

---

## The problem

India's public health supply chain runs on **reaction, not anticipation**.

Stock flows downward on a request-and-indent basis. A PHC pharmacist checks his register, notices he's low, raises an indent, and waits 7–21 days for delivery. Nothing in that chain looks ahead. By the time the indent is raised, the shelf is often already empty — and it stays empty for weeks.

The consequence isn't only clinical. Roughly **48% of Indian healthcare spending is out-of-pocket**, and about 70% of that goes to medicines. Every stock-out pushes a family from free public care into paying privately, or into going without.

<br>

> ### What already exists — and why it isn't enough
>
> India runs **DVDMS (e-Aushadhi)**, a C-DAC-built supply chain system deployed across most states, reaching down to PHC level. It is a capable transactional ledger.
>
> But three gaps remain:
>
> | Gap | Consequence |
> |---|---|
> | **It records, it doesn't predict** | Reports current stock and last month's use. Cannot say *"you run out in 11 days"* |
> | **It is state-siloed** | Telangana's warehouse cannot see Andhra Pradesh's surplus |
> | **Disease and stock never speak** | DVDMS knows inventory. IDSP knows outbreaks. No connection between them |

<br>

<div align="center">

### 💡 AarogyaGrid is not a replacement for DVDMS.
### It is the intelligence layer above it.

</div>

---

## How it works

```
     DVDMS / e-Aushadhi export
                │
                ▼
     ┌──────────────────────┐
     │  INGESTION SCHEMA    │  open OpenAPI spec, DVDMS-shaped records
     └──────────┬───────────┘  a state maps its existing export to this
                │
                ▼
     ┌──────────────────────┐
     │   FORECASTING        │  Ridge per SKU, point-in-time correct
     │                      │  + lagged IDSP surveillance features
     └──────────┬───────────┘  + per-SKU naive fallback
                │
                ▼
     ┌──────────────────────┐
     │   EARLY WARNING      │  days-to-stockout · reorder point
     │                      │  safety stock · 5 alert tiers
     └──────────┬───────────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│REDISTRIBUTE │   │   GEMINI    │  operational briefings
│ OR-Tools    │   │  BRIEFINGS  │  English + Telugu
│ min-cost    │   │  NL QUERY   │  question → data query
│ flow        │   └─────────────┘
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│  FEDERATION — coefficients only      │
│  across state nodes, no raw data     │
└──────────────────────────────────────┘
```

<br>

<table>
<tr>
<td width="33%" valign="top">

### 🔮 Predict
Ridge regression per medicine using **lagged disease surveillance**. Beats the best of three baselines on 6 of 8 medicines; the other 2 fall back to naive persistence by design.

</td>
<td width="33%" valign="top">

### ⚠️ Warn
Real inventory theory — reorder points, safety stock at 95% service level. Separates *already failed* from *still preventable*.

</td>
<td width="33%" valign="top">

### 🚚 Act
OR-Tools min-cost flow generates **executable transfer orders**: move 933 units from here to there, 61 km, 67 courses protected.

</td>
</tr>
</table>

---

## Results

### 📈 Forecasting — measured against three baselines

Every model is compared against **naive persistence**, a **7-day moving average**, and **seasonal naive (t-7)**. The table reports the best of the three.

<div align="center">

| Medicine | Ridge MAPE | Best baseline | Improvement | Model used |
|---|:---:|:---:|:---:|:---:|
| **Iron Folic Acid** | 12.83% | 13.94% | 🟢 **+7.9%** | Ridge |
| **Paracetamol 500mg** | 12.91% | 13.84% | 🟢 **+6.7%** | Ridge |
| **Amoxicillin 500mg** | 12.60% | 13.47% | 🟢 **+6.5%** | Ridge |
| **Metformin 500mg** | 12.48% | 13.36% | 🟢 **+6.5%** | Ridge |
| **Zinc Sulphate 20mg** | 12.84% | 13.61% | 🟢 **+5.6%** | Ridge |
| **ORS Sachet** | 11.69% | 12.36% | 🟢 **+5.4%** | Ridge |
| Artemether-Lumefantrine | 12.74% | 12.73% | −0.1% | Naive (fallback) |
| Ciprofloxacin 500mg | 18.45% | 15.91% | −16.0% | Naive (fallback) |

</div>

> **Two medicines are reported as failures, and the system falls back to naive persistence for them.**
>
> This is a deliberate design choice, not an oversight. Ridge helps where demand follows a trackable seasonal signal. It hurts where events are sparse and stochastic — cholera cases are rare enough that the surveillance feature is mostly noise, and the model overfits it. Per-SKU model selection is applied automatically on held-out data: if Ridge does not beat naive, naive is used in production.
>
> Full metrics — MAE, RMSE, WAPE and MAPE across all four models and all eight SKUs — are written to [`data/processed/forecast_metrics.csv`](data/processed/forecast_metrics.csv).

<br>

#### 🔬 Point-in-time correctness

IDSP surveillance is published **weekly, in arrears**. A forecast made on a Tuesday cannot use that week's completed case count — it does not exist yet.

All disease features are therefore lagged by at least one full week: `dis_w1` (previous reported week), `dis_w2`, and a four-week trailing mean. The weekly series is shifted **before** joining to daily records, so no same-week value can leak into the feature matrix.

This costs accuracy — an earlier version using same-week counts scored better — and that is the point. The reported figures are what the system would achieve in production.

<br>

### ⏱️ Warning, before the shelf is empty

<div align="center">

| 24 | 52 | 5.6 days | 18 |
|:---:|:---:|:---:|:---:|
| already at zero<br>*(the cost of no warning)* | preventable<br>stock-outs caught | median warning<br>lead time | alerts with<br>7–14 days notice |

</div>

<br>

### 🚚 Redistribution a district officer can execute

<div align="center">

| 52 | 40 | 55,227 | 3,377 |
|:---:|:---:|:---:|:---:|
| transfer orders | cross-district | units moved | treatment courses<br>protected |

</div>

**Sample output — not a chart, an instruction:**

```
MOVE 933 × Zinc Sulphate 20mg
  FROM  PHC Nalgonda 2 (Nalgonda) — 3,782 surplus units
  TO    CHC Yadadri Bhuvanagiri 1 — already at zero
  61.0 km · ~104 min · covers 67 treatment courses
```

Constraints enforced: the donor must retain its own reorder point, transferred batches must outlast the receiver's consumption window, distance is capped, and receiver storage capacity is respected.

<br>

### 🔒 Federated learning — the data-poor node gains most

<div align="center">

| Node | Training rows | Alone | Federated | Gain |
|---|:---:|:---:|:---:|:---:|
| Data-rich *(18 months)* | 6,780 | 9.50% | 9.48% | +0.2% |
| Moderate *(9 months)* | 2,532 | 10.69% | 10.05% | 🟢 **+6.0%** |
| Data-poor *(3 months)* | 310 | 23.78% | 19.04% | 🟢 **+19.9%** |

</div>

> A node with three months of history **cannot learn monsoon seasonality alone**. But seasonality is *shared structure* — so it can be learned collectively without pooling the underlying data.
>
> **What crosses a node boundary:** 13 model coefficients, 13 feature statistics.
> **What never leaves:** inventory records, patient counts, facility data.
>
> The gain scales inversely with local data volume, and nobody is made worse off — that monotonic relationship is the theoretical prediction, and it holds.
>
> **How the nodes are constructed:** they are simulated by partitioning our districts and giving each a deliberately different amount of training history. They carry state names in the interface to make the scenario legible, but the underlying facilities are all in Telangana. What is demonstrated is the *federation mechanism*, which is identical regardless of how nodes are partitioned.

---

## 🤖 Google AI integration

Gemini performs three distinct jobs, one of them on the **input** side of the system.

<table>
<tr>
<td width="50%" valign="top">

**Natural-language querying**
An officer types a question in plain English; Gemini translates it into a query over the facility data, which is validated against a blocklist and executed. This is Google AI operating *on* the data, not describing it.

**Evidence-grounded operational briefing**
Each alert becomes a three-sentence brief converting model outputs — stock level, burn rate, reorder point, transfer options — into an instruction. Gemini is not establishing causality; it is turning numbers into something actionable.

</td>
<td width="50%" valign="top">

**Multilingual delivery**
English for the district health officer, Telugu for the PHC pharmacist. Medicine names stay in English so they match the packaging.

**Model fallback chain**
Requests fall through a preference list of Gemini models, so a retired or overloaded model degrades gracefully instead of failing.

**Cached generation**
Briefings are generated ahead of time and cached to disk. The live demo never depends on an API call succeeding.

</td>
</tr>
</table>

**Natural-language query — unedited, including the user's typos:**

> **Asked:** *"Which CHS Are Running For Antibodies"*
>
> **Gemini generated:**
> ```python
> facility_type == "CHC" and (sku_name.str.contains("Ciprofloxacin")
>   or sku_name.str.contains("Amoxicillin")) and tier in ["CRITICAL","STOCKOUT"]
> ```
>
> Four correct rows returned. "CHS" for CHC, "antibodies" for antibiotics, no verb — and it still resolved the intent, mapped the drug class to two specific SKUs, and applied the right status filter.

**Operational briefing — unedited:**

> *PHC Yadadri Bhuvanagiri 7 will run out of Artemether-Lumefantrine in 14 days. Current stock has fallen below the reorder point of 209 units while the daily burn rate of 13.5 units remains high due to the peak monsoon season increasing malaria transmission. Please initiate an immediate stock transfer of 206 units from the surplus at PHC Nalgonda located 69.5 km away.*

The middle clause is the point. Gemini situated the burn rate in seasonal context — connecting an antimalarial to monsoon transmission — without that link being supplied in the prompt. It is interpretation grounded in the numbers passed to it, not a filled-in template.

---

## 📊 Data provenance

<div align="center">

**Live PHC inventory APIs are not publicly available in India.**<br>
We state this plainly rather than obscure it.

</div>

<br>

| Data | Source | Status |
|---|---|:---:|
| District structure, PHC/CHC counts | Real Telangana districts · IPHS norms (1 PHC ≈ 30,000 people) | ✅ **Real** |
| Medicine list | National List of Essential Medicines (NLEM) | ✅ **Real** |
| **Diarrhoeal incidence** | **NFHS-5 (2019–21), Telangana** — 5.46% two-week prevalence in under-5s | ✅ **Real, downloaded** |
| **Treatment rates** | **NFHS-5, Telangana** — 61.8% receive ORS, 39.3% receive zinc, 71.1% reach a provider | ✅ **Real, downloaded** |
| Seasonal shape | Modelled on published IDSP seasonal patterns | ⚠️ **Modelled** |
| Stock levels, receipts, issues | Derived from the above via documented clinical norms | 🔶 **Synthesised** |
| Bed occupancy, staff attendance | Generated against IPHS staffing and bed norms | 🔶 **Synthesised** |
| Road distances | Haversine × 1.35 rural road factor | 🔶 **Derived** |

Source file: [`data/raw/NFHS_5_Factsheets_Data.xls`](data/raw/) — downloaded from data.gov.in.

<br>

> ### On the ORS–diarrhoea correlation
>
> The dashboard shows ORS consumption tracking district diarrhoeal cases at **r = 0.960**. **This correlation is expected, not discovered** — consumption was *derived* from case counts at 6 sachets each, so the two series are related by construction.
>
> It validates that the generator applies clinical norms consistently across 18 months and three districts. It is **not** evidence that the data matches real PHC records, and we do not claim it is.

<br>

**What this data does not claim.** It is structurally plausible, not empirically validated. It reproduces the *shape* of the problem — monsoon demand spikes, indent-cycle sawtooth patterns, chronic under-supply in specific districts — but the specific numbers are not measurements of any real facility.

**Why that is sufficient for a prototype.** The system's value is in the pipeline, not the numbers: forecasting from surveillance, converting forecasts to reorder decisions, solving redistribution under constraints, and federating models without pooling data. Every one of those operates identically on real DVDMS records.

The generator is open source in [`src/generator/`](src/generator/). The ingestion schema ([`docs/openapi.yaml`](docs/openapi.yaml)) specifies the interface a state's DVDMS export connects to — published as an open specification so any vendor can implement against it. **The endpoints are specified but not yet implemented;** the schema itself is the Digital Public Good artifact, with field names mirroring DVDMS stock register columns so adoption requires mapping rather than restructuring.

---

## 🗺️ Prototype coverage

<div align="center">

```
INDIA
  └── TELANGANA                    ← prototype coverage
        ├── Nalgonda               12 PHC · 3 CHC
        ├── Yadadri Bhuvanagiri     8 PHC · 2 CHC
        └── Suryapet               10 PHC · 2 CHC
                                   ─────────────────
                                   37 facilities · 8 SKUs
```

</div>

The architecture is **state → district → facility**, so additional states connect as additional nodes without structural change. **The demonstration data is not national**, and the interface says so.

---

## 🚀 Running locally

```bash
git clone https://github.com/vigneshreddy29/aarogyagrid.git
cd aarogyagrid
pip install -r requirements.txt
```

Add a free Gemini key from [Google AI Studio](https://aistudio.google.com/apikey):

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

Build the pipeline:

```bash
python src/generator/build_data.py        # 1. data foundation
python src/forecast/train.py              # 2. train forecasters
python src/alerts/engine.py               # 3. compute alerts
python src/optimizer/redistribute.py      # 4. solve redistribution
python src/federated/fedavg.py            # 5. run federation
python src/generator/facility_status.py   # 6. bed + staff capacity
python src/gemini/briefs.py               # 7. generate briefings

python -m streamlit run app.py
```

<details>
<summary><b>Project structure</b></summary>

<br>

```
aarogyagrid/
├── app.py                            Streamlit dashboard, 7 views
├── docs/openapi.yaml                 open ingestion schema
├── data/raw/                         NFHS-5 source file
├── src/
│   ├── config.py                     districts, SKUs, NFHS-calibrated incidence
│   ├── generator/
│   │   ├── build_data.py             derives inventory from epidemiology
│   │   └── facility_status.py        beds and staff against IPHS norms
│   ├── forecast/train.py             Ridge + 3 baselines, point-in-time correct
│   ├── alerts/engine.py              reorder points, 5 alert tiers
│   ├── optimizer/redistribute.py     OR-Tools min-cost flow
│   ├── federated/fedavg.py           personalised FedAvg across nodes
│   └── gemini/
│       ├── client.py                 model fallback chain
│       ├── briefs.py                 operational briefings, EN + TE
│       └── nl_query.py               natural-language → data query
└── data/processed/                   parquet, cached briefings, metrics
```

</details>

---

## 🌏 Deployment path

<table>
<tr>
<td width="50%" valign="top">

### Within India
**District → State → National**

No new hardware. No new data collection. No behaviour change asked of frontline staff.

A state maps its existing DVDMS export to the published ingestion schema and receives forecasts, alerts, and transfer recommendations computed against data it already holds.

</td>
<td width="50%" valign="top">

### Across borders
**BRICS applicability**

The system's inputs are facility, item, stock level, consumption rate, and distance. Nothing in that list is India-specific.

Brazil and South Africa operate comparable primary health networks with the same stock-out problem — and the same data-sovereignty constraints federation is built to respect.

</td>
</tr>
</table>

---

## ⚖️ Known limitations

Stated here rather than left for a reviewer to find.

- **Coverage is one state.** Three Telangana districts, 37 facilities, 8 SKUs.
- **Inventory data is synthesised.** Derived from real epidemiology, but not measured.
- **Ingestion endpoints are specified, not implemented.** The schema is published; the server is not built.
- **Federation nodes are simulated** by partitioning districts with unequal training history, not by connecting real state systems.
- **Two SKUs fall back to naive forecasting** because Ridge does not beat the baseline on sparse, event-driven demand.
- **Bed and staff data are generated** against IPHS norms; no public API exposes them live.

---

<div align="center">

## Built with

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini-4285F4?style=flat-square&logo=google&logoColor=white)
![OR-Tools](https://img.shields.io/badge/OR--Tools-4285F4?style=flat-square&logo=google&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas&logoColor=white)

<br>

**[▶ Open the live demo](https://aarogyagrid-bwai.streamlit.app/)**

<br>

<sub>Build with AI: Code for Communities · Google Cloud × GDG India · 2026</sub>

</div>