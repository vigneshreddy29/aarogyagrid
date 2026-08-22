<div align="center">

# 🏥 AarogyaGrid

### Predictive stock-out prevention for India's primary health network

*DVDMS records what happened. AarogyaGrid predicts what's about to happen —<br>and tells districts what to do about it, without any state sharing its raw data.*

<br>

[![Live Demo](https://img.shields.io/badge/▶_Live_Demo-Open_App-FF4B4B?style=for-the-badge)](https://aarogyagrid-bwai.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/Google_Gemini-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)

![Status](https://img.shields.io/badge/status-working_prototype-success)
![License](https://img.shields.io/badge/license-MIT-blue)
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
     │   INGESTION API      │  open schema, DVDMS-shaped records
     └──────────┬───────────┘  a state points its existing export here
                │
                ▼
     ┌──────────────────────┐
     │   FORECASTING        │  Ridge per SKU
     │                      │  + IDSP disease surveillance features
     └──────────┬───────────┘
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
│REDISTRIBUTE │   │   GEMINI    │  causal briefs
│ OR-Tools    │   │   BRIEFS    │  English + Telugu
│ min-cost    │   └─────────────┘
│ flow        │
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
Ridge regression per medicine, using **district disease surveillance** as a predictive feature. Beats a seasonal-naive baseline on all 8 SKUs.

</td>
<td width="33%" valign="top">

### ⚠️ Warn
Real inventory theory — reorder points, safety stock at 95% service level. Separates *already failed* from *still preventable*.

</td>
<td width="33%" valign="top">

### 🚚 Act
OR-Tools min-cost flow generates **executable transfer orders**: move 282 units from here to there, 61 km, 20 courses protected.

</td>
</tr>
</table>

---

## Results

### 📈 Forecasting beats baseline on every medicine

<div align="center">

| Medicine | Ridge MAPE | Baseline | Improvement |
|---|:---:|:---:|:---:|
| **Artemether-Lumefantrine** (malaria) | 12.81% | 16.85% | 🟢 **24.0%** |
| **Ciprofloxacin 500mg** (cholera) | 17.95% | 22.82% | 🟢 **21.3%** |
| **ORS Sachet** (diarrhoeal) | 12.42% | 15.35% | 🟢 **19.1%** |
| Zinc Sulphate 20mg | 14.57% | 17.19% | 15.2% |
| Paracetamol 500mg | 13.57% | 15.66% | 13.3% |
| Metformin 500mg | 11.47% | 13.22% | 13.2% |
| Iron Folic Acid | 11.95% | 13.72% | 12.9% |
| Amoxicillin 500mg | 15.03% | 17.24% | 12.8% |

</div>

> **The top three improvements are all outbreak-driven medicines.** That is not coincidence — it is the disease surveillance feature carrying genuine predictive signal. Chronic medicines like Metformin, whose demand is flat, improve least. Exactly as theory predicts.

<br>

### ⏱️ Warning, before the shelf is empty

<div align="center">

| 23 | 52 | 5.7 days | 17 |
|:---:|:---:|:---:|:---:|
| already at zero<br>*(the cost of no warning)* | preventable<br>stock-outs caught | median warning<br>lead time | alerts with<br>7–14 days notice |

</div>

<br>

### 🚚 Redistribution a district officer can execute

<div align="center">

| 50 | 38 | 41,692 | 1,917 |
|:---:|:---:|:---:|:---:|
| transfer orders | cross-district | units moved | treatment courses<br>protected |

</div>

**Sample output — not a chart, an instruction:**

```
MOVE 282 × Zinc Sulphate 20mg
  FROM  PHC Nalgonda 2 (Nalgonda) — 1,160 surplus units
  TO    CHC Yadadri Bhuvanagiri 1 — already at zero
  61.0 km · ~104 min · covers 20 treatment courses
```

<br>

### 🔒 Federated learning — the data-poor state gains most

<div align="center">

| State node | Training rows | Alone | Federated | Gain |
|---|:---:|:---:|:---:|:---:|
| Telangana *(data-rich)* | 6,780 | 10.21% | 10.20% | +0.1% |
| Odisha *(moderate)* | 2,532 | 12.04% | 11.02% | 🟢 **+8.4%** |
| Meghalaya *(data-poor)* | 310 | 23.49% | 20.85% | 🟢 **+11.2%** |

</div>

> A state with three months of history **cannot learn monsoon seasonality alone**. But seasonality is *shared structure* across states — so it can be learned collectively without pooling the underlying data.
>
> **What crosses a state boundary:** 12 model coefficients, 12 feature statistics.
> **What never leaves:** inventory records, patient counts, facility data.
>
> The gain scales inversely with local data volume. Nobody is made worse off.

---

## 🤖 Google AI integration

Gemini does work that a template could not.

<table>
<tr>
<td width="50%" valign="top">

**Causal explanation**
Each alert becomes a three-sentence brief naming *why* depletion is happening — connecting burn rate, reorder point, and seasonal disease risk.

**Multilingual delivery**
English for the district health officer. Telugu for the PHC pharmacist. Medicine names preserved in English so they match the packaging.

</td>
<td width="50%" valign="top">

**Model fallback chain**
Requests fall through a preference list of Gemini models. A retired or overloaded model degrades gracefully instead of failing.

**Cached generation**
Briefs are generated ahead of time and cached to disk. The live demo never depends on an API call succeeding.

</td>
</tr>
</table>

**Unedited Gemini output:**

> *PHC Yadadri Bhuvanagiri 7 will run out of Artemether-Lumefantrine in 13 days. The current stock has fallen below the reorder point of 210 units due to a daily burn rate of 13.49 units, **which is exacerbated by the high malaria risk during the peak monsoon season**. An emergency district indent is required immediately to replenish supplies.*

That middle clause is the point. The model connected an antimalarial to monsoon transmission on its own — a causal claim, epidemiologically correct, not a filled-in template.

---

## 📊 Data provenance

<div align="center">

**Live PHC inventory APIs are not publicly available in India.**<br>
We state this plainly rather than obscure it.

</div>

<br>

| Data | Source | Status |
|---|---|:---:|
| District structure, PHC/CHC counts | Real Telangana districts · Indian norms (1 PHC ≈ 30,000 people) | ✅ **Real** |
| Medicine list | National List of Essential Medicines (NLEM) | ✅ **Real** |
| Disease seasonality | Modelled on published IDSP patterns for south Indian districts | ✅ **Real basis** |
| Clinical consumption rates | Standard treatment courses (ORS 6 sachets/case, ACT 1 course/case) | ✅ **Real** |
| Stock levels, receipts, issues | Derived from the above via documented clinical norms | 🔶 **Synthesised** |
| Road distances | Haversine × 1.35 rural road factor | 🔶 **Derived** |

<br>

<div align="center">

### Consumption is never invented — it is *computed* from epidemiology.

**ORS consumption correlates with district diarrhoeal cases at r = 0.960**

*Visible live on the "Why It Works" tab*

</div>

<br>

The generator is open source in [`src/generator/`](src/generator/). The ingestion API ([`docs/openapi.yaml`](docs/openapi.yaml)) is the interface a real state connects to swap synthesised data for live DVDMS records — no other change required.

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
python src/generator/build_data.py      # 1. data foundation
python src/forecast/train.py            # 2. train forecasters
python src/alerts/engine.py             # 3. compute alerts
python src/optimizer/redistribute.py    # 4. solve redistribution
python src/federated/fedavg.py          # 5. run federation
python src/gemini/briefs.py             # 6. generate briefs

python -m streamlit run app.py
```

<details>
<summary><b>Project structure</b></summary>

<br>

```
aarogyagrid/
├── app.py                          Streamlit dashboard
├── docs/openapi.yaml               open ingestion schema
├── src/
│   ├── config.py                   districts, SKUs, seasonality
│   ├── generator/build_data.py     derives inventory from epidemiology
│   ├── forecast/train.py           Ridge per SKU + disease features
│   ├── alerts/engine.py            reorder points, alert tiers
│   ├── optimizer/redistribute.py   OR-Tools min-cost flow
│   ├── federated/fedavg.py         personalised FedAvg across states
│   └── gemini/                     client, briefs, translation
└── data/processed/                 parquet + cached briefs
```

</details>

---

## 🗺️ Deployment path

<table>
<tr>
<td width="50%" valign="top">

### Within India
**District → State → National**

No new hardware. No new data collection. No behaviour change asked of frontline staff.

A state connects its existing DVDMS export to the ingestion API and immediately receives forecasts, alerts, and transfer recommendations computed against data it already holds.

</td>
<td width="50%" valign="top">

### Across borders
**BRICS applicability**

The system's inputs are facility, item, stock level, consumption rate, and distance. Nothing in that list is India-specific.

Brazil and South Africa operate comparable primary health networks with the same stock-out problem — and the same data-sovereignty constraints that federation is built to respect.

</td>
</tr>
</table>

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

<sub>Built for Build with AI: Code for Communities · Google Cloud × GDG India · 2026</sub>

</div>
