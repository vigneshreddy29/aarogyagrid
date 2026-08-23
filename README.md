<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0A0E1A,50:1A2336,100:5B8DEF&height=190&section=header&text=AarogyaGrid&fontSize=62&fontColor=ffffff&animation=fadeIn&fontAlignY=36&desc=Predictive%20stock-out%20prevention%20for%20India's%20primary%20health%20network&descAlignY=57&descSize=15" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=IBM+Plex+Mono&weight=500&size=19&duration=3600&pause=900&color=5B8DEF&center=true&vCenter=true&width=760&lines=DVDMS+records+what+happened.;AarogyaGrid+predicts+what's+about+to+happen.;And+tells+districts+what+to+do+about+it.;Without+any+state+sharing+its+raw+data." alt="tagline"/>

<br><br>

[![Live Demo](https://img.shields.io/badge/▶_Live_Demo-Open_App-FF4B4B?style=for-the-badge)](https://aarogyagrid-bwai.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/Google_Gemini-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)

![Status](https://img.shields.io/badge/status-working_prototype-success)
![Coverage](https://img.shields.io/badge/coverage-Telangana%3A_3_districts%2C_37_facilities-informational)
![Languages](https://img.shields.io/badge/languages-English_·_తెలుగు_·_हिन्दी-9333EA)
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
          ↓                   measured r = 0.741 against units issued
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
┌─────────────┐   ┌──────────────────┐
│REDISTRIBUTE │   │      GEMINI      │
│ OR-Tools    │   │  ask · advise ·  │
│ min-cost    │   │  explain · brief │
│ human       │   │  EN · తెలుగు · हिन्दी │
│ approval    │   └──────────────────┘
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│  FEDERATION — coefficients only      │
│  across nodes, no raw data           │
└──────────────────────────────────────┘
```

---

<div align="center">

## 💬 Ask AarogyaGrid

*The officer types a question. The system routes it three ways.*

</div>

| Mode | Question | What happens |
|---|---|---|
| **FILTER** | *"which CHCs are running out of antibiotics?"* | Gemini writes a pandas expression, it's validated against a blocklist, executed, and summarised |
| **ADVISE** | *"what should the district prioritise this week?"* | The live situation — alerts, resilience scores, staffing, available transfers — is passed to Gemini, which returns a briefing naming real facilities and quantities |
| **EXPLAIN** | *"how does the forecast work?"* | Answers from a fixed fact sheet about the model, never from general knowledge |

Routing uses deterministic keyword checks first, falling back to a Gemini classifier. Off-topic questions are declined rather than answered from training data.

**ADVISE output — unedited:**

> *Across Telangana, 37 facilities face critical alerts, with 10 high-risk centres and 21 facility-medicine pairs already completely at zero stock.*
>
> *The strain is concentrated in Yadadri Bhuvanagiri district, impacting CHC Bhongir, CHC Choutuppal and PHC Alair. ORS Sachets, Zinc Sulphate 20mg and Paracetamol 500mg dominate the stockouts, compounded by staff shortages averaging 83% of sanctioned capacity and dropping to 28.6% at PHC Yadagirigutta.*
>
> *Authorise immediate transfers this week from CHC Narketpally to send 881 ORS sachets to PHC Ramannapet, 200 to PHC Addagudur, and move 667 from PHC Nakrekal to CHC Bhongir. To stop recurrence, mandate automated redistribution triggers that act during the 5.8-day lead window before stocks hit zero.*

Every facility, medicine and quantity in that briefing is read from the live data. Nothing is invented.

**FILTER output — unedited, including the user's typos:**

> **Asked:** *"Which CHS Are Running For Antibodies"*
>
> ```python
> facility_type == "CHC" and (sku_name.str.contains("Ciprofloxacin")
>   or sku_name.str.contains("Amoxicillin")) and tier in ["CRITICAL","STOCKOUT"]
> ```
>
> "CHS" for CHC, "antibodies" for antibiotics, no verb — and it still resolved the intent, mapped the drug class to two specific SKUs, and applied the right status filter.

---

<div align="center">

## 🗣️ Multilingual by design

</div>

Operational content is delivered in **English, తెలుగు or हिन्दी** — briefings, recommendations, alert explanations, emergency conclusions and transfer instructions. Nine panels switch language at once.

**What is never translated:** medicine names and facility names. A pharmacist matching a translated drug name against an English box is a real failure mode.

**What stays in English:** navigation, data tables and the methodology section. District health reporting and stock registers in India are maintained in English, and the interface states this rather than leaving it looking unfinished.

---

## Results

### 📈 Forecasting — measured against three baselines

Every model is compared against **naive persistence**, a **7-day moving average**, and **seasonal naive (t-7)**. The table reports the best of the three.

<div align="center">

| Medicine | Ridge MAPE | Best baseline | Improvement | Model used |
|---|:---:|:---:|:---:|:---:|
| **Iron Folic Acid** | 11.75% | 12.62% | 🟢 **+6.9%** | Ridge |
| **Zinc Sulphate 20mg** | 12.40% | 13.28% | 🟢 **+6.6%** | Ridge |
| **Metformin 500mg** | 16.84% | 18.02% | 🟢 **+6.5%** | Ridge |
| **ORS Sachet** | 11.53% | 12.30% | 🟢 **+6.3%** | Ridge |
| **Amoxicillin 500mg** | 12.11% | 12.75% | 🟢 **+5.0%** | Ridge |
| **Paracetamol 500mg** | 13.94% | 14.51% | 🟢 **+3.9%** | Ridge |
| Artemether-Lumefantrine | 16.96% | 16.04% | 🔴 −5.7% | Naive (fallback) |
| Ciprofloxacin 500mg | 17.38% | 14.80% | 🔴 −17.4% | Naive (fallback) |

</div>

> **Two medicines are reported as failures, and the system falls back to naive persistence for them.**
>
> This is a deliberate design choice, not an oversight. Ridge helps where demand follows a trackable seasonal signal. It hurts where events are sparse and stochastic — antimalarials and cholera antibiotics have demand governed by discrete outbreaks rather than steady seasonal consumption, so the surveillance feature is mostly noise and the model overfits it. Per-SKU model selection is applied automatically on held-out data: if Ridge does not beat naive, naive is used in production.
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

| 21 | 37 | 5.8 days | 18 |
|:---:|:---:|:---:|:---:|
| already at zero<br>*(the cost of no warning)* | preventable<br>stock-outs caught | median warning<br>lead time | alerts with<br>7–14 days notice |

</div>

<br>

### 🚨 Emergency mode

A steady-state forecast cannot answer *"what if dengue doubles next week?"* Each scenario applies disease-specific demand multipliers and re-runs the same reorder arithmetic — nothing is retrained, which is exactly what would happen in production.

<div align="center">

| Scenario | At risk (normal → surge) | Newly critical | Warning time lost | Fail inside onset |
|---|:---:|:---:|:---:|:---:|
| **Flood displacement** | 58 → 113 | **50** | 25.4 days | 22 within 3 days |
| **Malaria surge** | 58 → 83 | 20 | **26.9 days** | 21 within 5 days |
| **Dengue outbreak** | 58 → 81 | 18 | 20.1 days | 28 within 7 days |
| **Heatwave** | 58 → 78 | 15 | 17.0 days | 6 within 2 days |

</div>

> A flood nearly doubles the number of facility-medicine pairs at risk — from 58 to 113 — and erases 25 days of warning. Twenty-two pairs deplete inside the 3-day onset window, faster than a district indent can be raised and delivered. Pre-positioning has to happen before the surge is visible in case counts.

<br>

### 🚚 Redistribution a district officer can execute

<div align="center">

| 71 | 64 | 43,697 | 3,462 |
|:---:|:---:|:---:|:---:|
| transfer orders | cross-district | units moved | treatment courses<br>protected |

</div>

**Sample output — not a chart, an instruction:**

```
MOVE 881 × ORS Sachet (WHO formula)
  FROM  CHC Narketpally (Nalgonda) — 6,570 surplus units
  TO    PHC Ramannapet (Yadadri Bhuvanagiri) — already at zero
  17.8 km · ~30 min · covers 147 treatment courses
```

Constraints enforced: the donor must retain its own reorder point, transferred batches must outlast the receiver's consumption window, distance is capped at 75 km, and receiver storage capacity is respected.

**Every order requires human authorisation.** Approve, Modify or Reject sits on each recommendation. The optimiser proposes; a district officer decides. Stock transfers carry clinical and audit consequences a solver cannot weigh.

<br>

> ### 📏 Order-of-magnitude scale
>
> The prototype protects 3,462 treatment courses across 37 facilities in one redistribution cycle — about 94 per facility. India operates roughly 30,000 PHCs and 5,700 CHCs. If a comparable share of facilities carried surplus within transfer range, a single national cycle would move medicine covering **on the order of 3 million treatment courses**.
>
> This is arithmetic, not a projection. Our demonstration district was constructed to be under acute supply stress, so its per-facility rate is higher than a national average would be. It indicates scale; it does not forecast benefit.

<br>

### 🔒 Federated learning — the data-poor node gains most

<div align="center">

| Node | Training rows | Alone | Federated | Gain |
|---|:---:|:---:|:---:|:---:|
| Data-rich *(18 months)* | 6,780 | 9.48% | 9.51% | −0.4% |
| Moderate *(9 months)* | 2,532 | 10.59% | 10.22% | 🟢 **+3.5%** |
| Data-poor *(3 months)* | 310 | 25.32% | 18.98% | 🟢 **+25.0%** |

</div>

> A node with three months of history **cannot learn monsoon seasonality alone**. But seasonality is *shared structure* — so it can be learned collectively without pooling the underlying data.
>
> **What crosses a node boundary:** 13 model coefficients, 13 feature statistics.
> **What never leaves:** inventory records, patient counts, facility data.
>
> The gain scales inversely with local data volume: **data-rich nodes are essentially unaffected (within ±0.5%), while data-poor nodes gain substantially.** The blend weight is set by each node's own data volume, so a node with abundant history keeps its local model almost entirely — which is why the data-rich result sits marginally on either side of zero rather than improving.
>
> **How the nodes are constructed:** they are simulated by partitioning our districts and giving each a deliberately different amount of training history. They carry state names in the interface to make the scenario legible, but the underlying facilities are all in Telangana. What is demonstrated is the *federation mechanism*, which is identical regardless of how nodes are partitioned.

---

## 🤖 Google AI integration

Gemini performs four distinct jobs, two of them on the **input** side of the system.

<table>
<tr>
<td width="50%" valign="top">

**Natural-language querying**
A question becomes a validated pandas expression, executed against live data and summarised. Google AI operating *on* the data, not describing it.

**Situational advice**
The live alert, resilience, staffing and transfer state is passed as context; Gemini returns a briefing naming real facilities and quantities.

</td>
<td width="50%" valign="top">

**Evidence-grounded briefings**
Each alert becomes three sentences converting model outputs into an instruction. Gemini is not establishing causality; it turns numbers into something actionable.

**Multilingual delivery**
Nine operational panels in English, Telugu or Hindi. Medicine and facility names are never translated.

</td>
</tr>
</table>

**Reliability:** requests fall through a preference list of Gemini models, so a retired or overloaded model degrades gracefully. Alert briefings are generated ahead of time and cached to disk, so the demo never depends on a live API call succeeding.

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
| **Seasonal shape** | **Calibrated against 218 IDSP outbreak reports for Telangana (2009–2023)** via EpiClim (Zenodo 14580510, arXiv 2501.18602) — diarrhoeal outbreaks cluster in Jul, Aug, Jun, Sep; vector-borne in Aug, Jul, Sep | ✅ **Real, downloaded** |
| Stock levels, receipts, issues | Derived from the above via documented clinical norms | 🔶 **Synthesised** |
| Patient footfall | Derived from incidence, catchment and IPHS service-load norms | 🔶 **Synthesised** |
| Bed occupancy, staff attendance | Generated against IPHS staffing and bed norms | 🔶 **Synthesised** |
| Road distances | Haversine × 1.35 rural road factor | 🔶 **Derived** |

**Source files:** [`data/raw/NFHS_5_Factsheets_Data.xls`](data/raw/) (data.gov.in) · [`data/raw/Final_data.csv`](data/raw/) (EpiClim, Zenodo) · facility placement in [`src/mandals.py`](src/mandals.py).

<br>

> ### On the seasonality calibration
>
> IDSP records outbreak **reports**, not routine caseload. A low-report month means fewer outbreaks were declared, not that incidence collapsed.
>
> We therefore use the IDSP monthly distribution as the **shape** of the seasonality curve, compressed around 1.0 to keep amplitude plausible for routine demand. The peak ordering is preserved exactly; the amplitude is not taken literally.

<br>

> ### On the two correlations
>
> **ORS vs diarrhoea, r = 0.960 — expected, not discovered.** Consumption was *derived* from case counts at 6 sachets each, so the two series are related by construction. It validates that the generator applies clinical norms consistently across 18 months and three districts. It is **not** evidence that the data matches real PHC records, and we do not claim it is.
>
> **Footfall vs demand, median r = 0.741 across facilities, 28 of 37 above 0.5 — a different measurement.** It tests whether patient volume predicts medicine movement, computed weekly and only on days when stock was actually available. A facility that has run out issues nothing regardless of how many patients arrive; including those days would mask the relationship rather than measure it.

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

## 🖥️ The console — nine views

| View | What it answers |
|---|---|
| **Alert Map** | Where is the crisis concentrated? Every colour is a forecast, not a reading |
| **Patient Footfall** | Does patient volume actually move medicine? (r = 0.741) |
| **Emergency Mode** | What happens if dengue doubles, or a flood hits? |
| **Preventable Stock-outs** | Which facilities still have time, and how much? |
| **Redistribution Plan** | Which transfers to authorise — with Approve / Modify / Reject |
| **AI Briefings** | The alert as an instruction, English beside Telugu |
| **Federated Learning** | Does sharing weights help, and who does it help most? |
| **PHC Resilience Index** | Where should the district intervene first? |
| **Why It Works** | What is real, what is synthesised, and what we do not claim |

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
├── data/raw/                         NFHS-5 and EpiClim source files
├── src/
│   ├── config.py                     districts, SKUs, calibrated incidence
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
│       └── nl_query.py               routing, querying, advice, translation
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
- **Two SKUs fall back to naive forecasting** (antimalarials and cholera antibiotics) because Ridge does not beat the baseline on sparse, event-driven demand.
- **Seasonality is calibrated on outbreak reports, not routine incidence.** The curve's shape is empirical; its amplitude is a modelling choice.
- **The Resilience Index is a prototype policy instrument.** Its weights are a starting proposal and would need calibration against outcome data before operational use.
- **The pipeline is run as ten scripts**, not an automated orchestration.

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

### [▶ Open the live demo](https://aarogyagrid-bwai.streamlit.app/)

<br>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:5B8DEF,50:1A2336,100:0A0E1A&height=110&section=footer" width="100%"/>

<sub>Build with AI: Code for Communities · Google Cloud × GDG India · 2026</sub>

</div>