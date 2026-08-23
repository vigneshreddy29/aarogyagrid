<div align="center">

# 🏥 AarogyaGrid

### Predictive stock-out prevention for India's primary health network

*DVDMS records what happened. AarogyaGrid predicts what's about to happen —<br>and tells districts what to do about it, without any state sharing its raw data.*

<br>

[![Live Demo](https://img.shields.io/badge/▶_Live_Demo-Open_App-FF4B4B?style=for-the-badge)](https://aarogyagrid-bwai.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/Google_Gemini-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)

![Status](https://img.shields.io/badge/status-working_prototype-success)
![Coverage](https://img.shields.io/badge/coverage-Telangana%3A_3_districts%2C_37_facilities-informational)
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

## The demand chain

The problem statement asks for visibility into medicines, **patient footfall**, and resource utilisation. Footfall is the operational link most systems skip — a case only consumes medicine once the patient walks in.

```
   DISEASE INCIDENCE          IDSP surveillance, weekly
          ↓
   FACILITY-SEEKING           NFHS-5: 71.1% of cases reach a provider
          ↓
   PATIENT FOOTFALL           OPD · IPD · emergency · referrals
          ↓                   measured r = 0.881 against units issued
   MEDICINE DEMAND            clinical treatment courses
          ↓
   STOCK DEPLETION            reorder point · safety stock · days remaining
```

<br>

## System architecture

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
     └──────────┬───────────┘  + emergency surge scenarios
                │
       ┌────────┴────────┐
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│REDISTRIBUTE │   │   GEMINI    │  operational briefings
│ OR-Tools    │   │  BRIEFINGS  │  English + Telugu
│ min-cost    │   │  NL QUERY   │  question → data query
│ human       │   └─────────────┘
│ approval    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│  FEDERATION — coefficients only      │
│  across nodes, no raw data           │
└──────────────────────────────────────┘
```

---

## Results

### 📈 Forecasting — measured against three baselines

Every model is compared against **naive persistence**, a **7-day moving average**, and **seasonal naive (t-7)**. The table reports the best of the three.

<div align="center">

| Medicine | Ridge MAPE | Best baseline | Improvement | Model used |
|---|:---:|:---:|:---:|:---:|
| **Metformin 500mg** | 12.51% | 13.54% | 🟢 **+7.6%** | Ridge |
| **Paracetamol 500mg** | 11.36% | 12.28% | 🟢 **+7.5%** | Ridge |
| **Amoxicillin 500mg** | 13.01% | 14.00% | 🟢 **+7.1%** | Ridge |
| **Iron Folic Acid** | 11.76% | 12.64% | 🟢 **+7.0%** | Ridge |
| **ORS Sachet** | 11.82% | 12.54% | 🟢 **+5.8%** | Ridge |
| **Zinc Sulphate 20mg** | 15.48% | 16.14% | 🟢 **+4.1%** | Ridge |
| **Artemether-Lumefantrine** | 13.22% | 13.39% | 🟢 **+1.3%** | Ridge |
| Ciprofloxacin 500mg | 18.91% | 16.39% | −15.4% | Naive (fallback) |

</div>

> **One medicine is reported as a failure, and the system falls back to naive persistence for it.**
>
> This is a deliberate design choice, not an oversight. Ridge helps where demand follows a trackable seasonal signal. It hurts where events are sparse and stochastic — cholera cases are rare enough that the surveillance feature is mostly noise, and the model overfits it. Per-SKU model selection is applied automatically on held-out data: if Ridge does not beat naive, naive is used in production.
>
> Full metrics — MAE, RMSE, WAPE and MAPE across all four models and all eight SKUs — are written to [`data/processed/forecast_metrics.csv`](data/processed/forecast_metrics.csv).
>
> ⚠️ **Measured on synthetic inventory data**, so real-world performance on live PHC records would differ. What the comparison establishes is that lagged surveillance features carry predictive signal beyond consumption history alone.

<br>

#### 🔬 Point-in-time correctness

IDSP surveillance is published **weekly, in arrears**. A forecast made on a Tuesday cannot use that week's completed case count — it does not exist yet.

All disease features are therefore lagged by at least one full week: `dis_w1` (previous reported week), `dis_w2`, and a four-week trailing mean. The weekly series is shifted **before** joining to daily records, so no same-week value can leak into the feature matrix.

This costs accuracy — an earlier version using same-week counts scored substantially better — and that is the point. The reported figures are what the system would achieve in production.

<br>

### ⏱️ Warning, before the shelf is empty

<div align="center">

| 22 | 50 | 6.0 days | 18 |
|:---:|:---:|:---:|:---:|
| already at zero<br>*(the cost of no warning)* | preventable<br>stock-outs caught | median warning<br>lead time | alerts with<br>7–14 days notice |

</div>

<br>

### 🚨 Emergency mode

A steady-state forecast cannot answer *"what if dengue doubles next week?"* Each scenario applies disease-specific demand multipliers and re-runs the same reorder arithmetic — nothing is retrained, which is exactly what would happen in production.

<div align="center">

| Scenario | At risk (normal → surge) | Newly critical | Warning time lost | Fail inside onset window |
|---|:---:|:---:|:---:|:---:|
| **Flood displacement** | 72 → 103 | **30** | **23.8 days** | 26 within 3 days |
| **Dengue outbreak** | 72 → 91 | 18 | 18.6 days | 35 within 7 days |
| **Malaria surge** | 72 → 88 | 15 | 19.0 days | 25 within 5 days |
| **Heatwave** | 72 → 87 | 14 | 14.8 days | 8 within 2 days |

</div>

> A flood erases **nearly 24 days of warning** across affected medicines. Twenty-six facility-medicine pairs deplete inside the 3-day onset window — faster than a district indent can be raised and delivered. Pre-positioning has to happen before the surge is visible in case counts.

<br>

### 🚚 Redistribution a district officer can execute

<div align="center">

| 92 | 83 | 89,690 | 6,927 |
|:---:|:---:|:---:|:---:|
| transfer orders | cross-district | units moved | treatment courses<br>protected |

</div>

**Sample output — not a chart, an instruction:**

```
MOVE 1,610 × ORS Sachet (WHO formula)
  FROM  CHC Narketpally (Nalgonda) — 7,794 surplus units
  TO    PHC Valigonda (Yadadri Bhuvanagiri) — already at zero
  34.4 km · ~58 min · covers 268 treatment courses
```

Constraints enforced: the donor must retain its own reorder point, transferred batches must outlast the receiver's consumption window, distance is capped at 75 km, and receiver storage capacity is respected.

**Every order requires human authorisation.** The optimiser proposes; a district officer approves, modifies or rejects. Stock transfers carry clinical and audit consequences a solver cannot weigh.

<br>

### 🔒 Federated learning — the data-poor node gains most

<div align="center">

| Node | Training rows | Alone | Federated | Gain |
|---|:---:|:---:|:---:|:---:|
| Data-rich *(18 months)* | 6,780 | 9.11% | 9.08% | +0.3% |
| Moderate *(9 months)* | 2,532 | 12.96% | 12.45% | 🟢 **+3.9%** |
| Data-poor *(3 months)* | 310 | 19.45% | 17.45% | 🟢 **+10.3%** |

</div>

> A node with three months of history **cannot learn monsoon seasonality alone**. But seasonality is *shared structure* — so it can be learned collectively without pooling the underlying data.
>
> **What crosses a node boundary:** 13 model coefficients, 13 feature statistics.
> **What never leaves:** inventory records, patient counts, facility data.
>
> The gain scales inversely with local data volume, and nobody is made worse off — that monotonic relationship is the theoretical prediction for federated averaging, and it holds.
>
> **How the nodes are constructed:** they are simulated by partitioning our districts and giving each a deliberately different amount of training history. They carry state names in the interface to make the scenario legible, but the underlying facilities are all in Telangana. What is demonstrated is the *federation mechanism*, which is identical regardless of how nodes are partitioned.

---

## 🤖 Google AI integration

Gemini performs three distinct jobs, one of them on the **input** side of the system.

<table>
<tr>
<td width="50%" valign="top">

**Natural-language querying**
An officer types a question in plain English; Gemini translates it into a query over the facility data, which is validated against a blocklist and executed, then summarised as an actionable brief. This is Google AI operating *on* the data, not describing it.

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
> Correct rows returned. "CHS" for CHC, "antibodies" for antibiotics, no verb — and it still resolved the intent, mapped the drug class to two specific SKUs, and applied the right status filter.

**Operational briefing — unedited:**

> *PHC Alair will run out of Iron Folic Acid in 13.5 days. Current stock has fallen to 1,656 units against the reorder point of 1,935 units due to a daily burn rate of 122.77 units. Request an immediate stock transfer from PHC Addagudur, located 34.9 km away.*

Three sentences: what happens, why, and the specific action — with a named source facility and a real distance.

---

## 📊 Data provenance

<div align="center">

**Live PHC inventory APIs are not publicly available in India.**<br>
We state this plainly rather than obscure it.

</div>

<br>

| Data | Source | Status |
|---|---|:---:|
| **Facility locations** | Real Telangana mandal headquarters — Indian PHCs are sited at mandal HQ under IPHS. Six are confirmed PHC sites in NHM's published Hospital Development Society list | ✅ **Real** |
| District structure, PHC/CHC counts | Real districts · IPHS norms (1 PHC ≈ 30,000 people, 1 CHC ≈ 120,000) | ✅ **Real** |
| Medicine list | National List of Essential Medicines (NLEM) | ✅ **Real** |
| **Diarrhoeal incidence** | **NFHS-5 (2019–21), Telangana** — 5.46% two-week prevalence in under-5s | ✅ **Real, downloaded** |
| **Treatment rates** | **NFHS-5, Telangana** — 61.8% receive ORS, 39.3% receive zinc, 71.1% reach a provider | ✅ **Real, downloaded** |
| Seasonal shape | Modelled on published IDSP seasonal patterns | ⚠️ **Modelled** |
| Stock levels, receipts, issues | Derived from the above via documented clinical norms | 🔶 **Synthesised** |
| Patient footfall | Derived from incidence, catchment and IPHS service-load norms | 🔶 **Synthesised** |
| Bed occupancy, staff attendance | Generated against IPHS staffing and bed norms | 🔶 **Synthesised** |
| Road distances | Haversine × 1.35 rural road factor | 🔶 **Derived** |

Source file: [`data/raw/NFHS_5_Factsheets_Data.xls`](data/raw/) — downloaded from data.gov.in.
Facility placement: [`src/mandals.py`](src/mandals.py).

<br>

> ### On the ORS–diarrhoea correlation
>
> The dashboard shows ORS consumption tracking district diarrhoeal cases at **r = 0.960**. **This correlation is expected, not discovered** — consumption was *derived* from case counts at 6 sachets each, so the two series are related by construction.
>
> It validates that the generator applies clinical norms consistently across 18 months and three districts. It is **not** evidence that the data matches real PHC records, and we do not claim it is.
>
> The **footfall → demand** correlation (r = 0.881 median) is a different measurement: it tests whether patient volume predicts medicine movement, computed weekly and only on days when stock was actually available. A facility that has run out issues nothing regardless of how many patients arrive — including those days would mask the relationship rather than measure it.

<br>

**What this data does not claim.** It is structurally plausible, not empirically validated. It reproduces the *shape* of the problem — monsoon demand spikes, indent-cycle sawtooth patterns, chronic under-supply in specific districts — but the specific numbers are not measurements of any real facility.

**Why that is sufficient for a prototype.** The system's value is in the pipeline, not the numbers: forecasting from surveillance, converting forecasts to reorder decisions, solving redistribution under constraints, and federating models without pooling data. Every one of those operates identically on real DVDMS records.

The ingestion schema ([`docs/openapi.yaml`](docs/openapi.yaml)) specifies the interface a state's DVDMS export connects to — published as an open specification so any vendor can implement against it. **The endpoints are specified but not yet implemented;** the schema itself is the Digital Public Good artifact, with field names mirroring DVDMS stock register columns so adoption requires mapping rather than restructuring.

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
python src/generator/build_data.py        # 1. facilities, disease, stock ledger
python src/forecast/train.py              # 2. train forecasters
python src/alerts/engine.py               # 3. compute alerts
python src/optimizer/redistribute.py      # 4. solve redistribution
python src/federated/fedavg.py            # 5. run federation
python src/generator/facility_status.py   # 6. beds and staff
python src/generator/footfall.py          # 7. patient footfall
python src/alerts/resilience.py           # 8. resilience index
python src/alerts/emergency.py            # 9. surge scenarios
python src/gemini/briefs.py               # 10. operational briefings

python -m streamlit run app.py
```

<details>
<summary><b>Project structure</b></summary>

<br>

```
aarogyagrid/
├── app.py                            Streamlit console, 9 views
├── style.py                          visual layer
├── docs/openapi.yaml                 open ingestion schema
├── data/raw/                         NFHS-5 source file
├── src/
│   ├── config.py                     districts, SKUs, NFHS-calibrated incidence
│   ├── mandals.py                    real Telangana mandal locations
│   ├── generator/
│   │   ├── build_data.py             derives inventory from epidemiology
│   │   ├── facility_status.py        beds and staff against IPHS norms
│   │   └── footfall.py               OPD, IPD, emergency, referrals
│   ├── forecast/train.py             Ridge + 3 baselines, point-in-time correct
│   ├── alerts/
│   │   ├── engine.py                 reorder points, 5 alert tiers
│   │   ├── resilience.py             composite operational index
│   │   └── emergency.py              surge scenario simulation
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
- **Inventory, footfall, bed and staff data are synthesised.** Derived from real epidemiology and IPHS norms, but not measured.
- **Facility coordinates are mandal headquarters**, accurate to 1–2 km, not surveyed facility entrances.
- **Ingestion endpoints are specified, not implemented.** The schema is published; the server is not built.
- **Federation nodes are simulated** by partitioning districts with unequal training history, not by connecting real state systems.
- **One SKU falls back to naive forecasting** because Ridge does not beat the baseline on sparse, event-driven demand.
- **The Resilience Index is a prototype policy instrument.** Its weights are a starting proposal and would need calibration against outcome data before operational use.

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