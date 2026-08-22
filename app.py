"""AarogyaGrid — dashboard."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.gemini.nl_query import run as nl_run, summarise

st.set_page_config(page_title="AarogyaGrid", page_icon="🏥", layout="wide")

OUT = "data/processed"


@st.cache_data
def load(v="4"):
    import json, os

    briefs, fed = {}, []
    if os.path.exists(f"{OUT}/briefs.json"):
        briefs = json.load(open(f"{OUT}/briefs.json", encoding="utf-8"))
    if os.path.exists(f"{OUT}/federation.json"):
        fed = json.load(open(f"{OUT}/federation.json", encoding="utf-8"))

    alerts    = pd.read_parquet(f"{OUT}/alerts.parquet")
    transfers = pd.read_parquet(f"{OUT}/transfers.parquet")
    disease   = pd.read_parquet(f"{OUT}/disease_weekly.parquet")
    ledger    = pd.read_parquet(f"{OUT}/stock_ledger.parquet")
    status    = pd.read_parquet(f"{OUT}/facility_status.parquet")
    resil     = pd.read_parquet(f"{OUT}/resilience.parquet")

    # Parquet can restore these as object dtype on a fresh container,
    # which breaks the .dt accessor. Coerce explicitly.
    disease["week_start"] = pd.to_datetime(disease["week_start"], errors="coerce")
    ledger["date"]        = pd.to_datetime(ledger["date"], errors="coerce")

    return alerts, transfers, disease, ledger, briefs, fed, status, resil


alerts, transfers, disease, ledger, briefs, fed, status, resil = load("4")

TIER_COLOR = {"STOCKOUT": "#8B0000", "CRITICAL": "#DC2626",
              "WARNING": "#F59E0B", "WATCH": "#FCD34D", "OK": "#10B981"}

BAND_COLOR = {"HIGH RISK": "#DC2626", "AT RISK": "#F59E0B",
              "STABLE": "#FCD34D", "RESILIENT": "#10B981"}

st.title("AarogyaGrid")
st.caption("Predictive stock-out prevention for India's primary health network — "
           "a forecasting and redistribution layer above existing DVDMS/e-Aushadhi systems")
st.caption("**Prototype coverage:** Telangana — 3 districts, 37 facilities. "
           "The architecture is state → district → facility, so additional states "
           "connect as additional nodes. The demonstration data is not national.")

# ---------------------------------------------------------------- KPIs
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Facilities monitored", alerts.facility_id.nunique())
c2.metric("High risk facilities", int((resil.band == "HIGH RISK").sum()),
          help="Resilience score below 50 — supply, staffing and capacity combined")
c3.metric("Already stocked out", int((alerts.tier == "STOCKOUT").sum()),
          help="Failures that early warning would have prevented")
c4.metric("Preventable stock-outs", int((alerts.tier == "CRITICAL").sum()),
          help="Stock remains, but will deplete before resupply")
c5.metric("Courses protected", f"{int(transfers.courses_covered.sum()):,}")

st.divider()

# ---------------------------------------------------------------- NL query
with st.expander("🔍 **Ask a question** — natural language search across all facilities",
                 expanded=False):
    st.caption("Gemini translates your question into a query over the facility "
               "data. Try: *understaffed facilities in Yadadri running out of "
               "antimalarials* · *facilities at bed capacity that are also "
               "running out of medicine* · *which PHCs are already out of ORS*")

    q = st.text_input("Question",
                      placeholder="e.g. which CHCs are running out of antibiotics?",
                      label_visibility="collapsed")

    if q:
        with st.spinner("Interpreting…"):
            try:
                res, expr, err = nl_run(q)
            except Exception as e:
                res, expr, err = None, None, str(e)

        if err:
            st.error(err)
            if expr:
                st.code(expr, language="text")
        elif res is None or len(res) == 0:
            st.info("No facilities match that query.")
            if expr:
                st.code(expr, language="text")
        else:
            with st.spinner("Summarising…"):
                try:
                    brief = summarise(q, res)
                except Exception:
                    brief = ""

            if brief:
                st.info(brief)
            st.caption(f"{len(res)} matching facility-medicine pairs")
            st.dataframe(
                res[["facility_name", "facility_type", "district", "sku_name",
                     "current_stock", "days_to_stockout", "tier",
                     "occupancy_pct", "staff_present_pct"]],
                use_container_width=True, hide_index=True, height=300)
            with st.expander("Query Gemini generated"):
                st.code(expr, language="python")
                st.caption("Validated against a blocklist before execution — "
                           "only read operations on the in-memory dataframe "
                           "are permitted.")

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["Alert Map", "Preventable Stock-outs", "Redistribution Plan",
     "AI Briefings", "Federated Learning", "Resilience Score", "Why It Works"])

# ---------------------------------------------------------------- map
with tab1:
    worst = (alerts.assign(rank=alerts.tier.map(
                {"STOCKOUT": 0, "CRITICAL": 1, "WARNING": 2, "WATCH": 3, "OK": 4}))
             .sort_values("rank").groupby("facility_id", as_index=False).first())

    fig = px.scatter_map(
        worst, lat="latitude", lon="longitude", color="tier",
        color_discrete_map=TIER_COLOR, size="catchment_population",
        size_max=22, zoom=7.2, height=520,
        hover_name="facility_name",
        hover_data={"district": True, "sku_name": True,
                    "days_to_stockout": True, "latitude": False, "longitude": False},
        map_style="carto-positron")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(alerts.tier.value_counts().rename("facility-SKU pairs"),
                 use_container_width=True)

# ---------------------------------------------------------------- preventable
with tab2:
    st.subheader("Stock still available — depletion predicted before resupply")
    crit = alerts[alerts.tier == "CRITICAL"].sort_values("days_to_stockout")

    lead = st.slider("Minimum warning lead time (days)", 0, 14, 0)
    show = crit[crit.days_to_stockout >= lead]
    st.caption(f"{len(show)} alerts with at least {lead} days of warning · "
               f"median lead time {crit.days_to_stockout.median():.1f} days")

    st.dataframe(
        show[["facility_name", "district", "sku_name", "current_stock",
              "daily_burn", "days_to_stockout", "reorder_point"]],
        use_container_width=True, height=340, hide_index=True)

    if len(show):
        pick = st.selectbox("Inspect facility-SKU",
                            show.apply(lambda r: f"{r.facility_name} — {r.sku_name}",
                                       axis=1))
        fn, sn = pick.split(" — ")
        row = show[(show.facility_name == fn) & (show.sku_name == sn)].iloc[0]

        hist = ledger[(ledger.facility_id == row.facility_id) &
                      (ledger.sku_code == row.sku_code)].tail(120)

        f = go.Figure()
        f.add_scatter(x=hist.date, y=hist.closing_stock, name="Stock on hand",
                      line=dict(color="#2563EB", width=2))
        f.add_hline(y=row.reorder_point, line_dash="dash", line_color="#F59E0B",
                    annotation_text="Reorder point")
        f.add_hline(y=0, line_color="#DC2626")
        f.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                        yaxis_title="Units")
        st.plotly_chart(f, use_container_width=True)

        st.info(f"**{row.facility_name}** has **{int(row.current_stock)} units** of "
                f"{row.sku_name}, burning **{row.daily_burn}/day** — depletion in "
                f"**{row.days_to_stockout} days**, against a reorder point of "
                f"**{int(row.reorder_point)} units**.")

# ---------------------------------------------------------------- transfers
with tab3:
    st.subheader("Recommended transfers — surplus to shortage")
    st.caption(f"{len(transfers)} orders · "
               f"{int(transfers.cross_district.sum())} cross-district · "
               f"{int(transfers.quantity.sum()):,} units · "
               f"mean {transfers.road_km.mean():.0f} km")

    for r in transfers.head(12).itertuples():
        with st.container(border=True):
            a, b = st.columns([3, 1])
            a.markdown(
                f"**Move {r.quantity:,} × {r.sku_name}**  \n"
                f"FROM **{r.from_facility}** ({r.from_district}) — "
                f"{r.from_surplus_units:,} surplus units  \n"
                f"TO **{r.to_facility}** ({r.to_district}) — "
                f"{'already at zero' if r.to_days_to_stockout == 0 else f'{r.to_days_to_stockout} days to stock-out'}")
            b.metric("Distance", f"{r.road_km} km", f"~{r.drive_min} min")
            b.caption(f"{int(r.courses_covered)} treatment courses")

# ---------------------------------------------------------------- AI briefs
with tab4:
    st.subheader("Gemini-generated field briefings")
    st.caption("Each alert is converted into an operational briefing an officer "
               "can act on, and translated for the PHC pharmacist. Gemini "
               "receives stock level, burn rate, reorder point, season and "
               "transfer options — and turns them into an instruction. "
               "Generated ahead of time and cached.")

    if not briefs:
        st.warning("No briefs cached. Run `python src/gemini/briefs.py`.")
    else:
        items = sorted(briefs.items(), key=lambda kv: kv[1]["days_to_stockout"])
        labels = [f"{v['facility']} — {v['sku']} ({v['days_to_stockout']:.0f}d)"
                  for _, v in items]
        idx = st.selectbox("Select alert", range(len(labels)),
                           format_func=lambda i: labels[i])
        b = items[idx][1]

        a, c = st.columns(2)
        with a:
            st.markdown("**English — district health officer**")
            st.info(b["english"])
        with c:
            st.markdown("**తెలుగు — PHC pharmacist**")
            st.success(b["telugu"] or "—")

        st.caption(f"{len(briefs)} briefings cached across "
                   f"{len({v['facility'] for v in briefs.values()})} facilities")

# ---------------------------------------------------------------- federation
with tab5:
    st.subheader("Federated learning across nodes")
    st.caption("Each node trains on its own data. Only model coefficients and "
               "feature statistics are exchanged — no inventory records, no "
               "patient data, no facility rows cross a node boundary.")

    st.info(
        "**How these nodes are constructed.** The three nodes are simulated by "
        "partitioning our districts and giving each a deliberately different "
        "amount of training history — 18, 9 and 3 months. They carry state names "
        "to make the scenario legible, but the underlying facilities are all in "
        "Telangana. What is demonstrated is the *federation mechanism*, which is "
        "identical regardless of how nodes are partitioned: each node trains "
        "locally, shares only weights, and receives a blended model weighted by "
        "its own data volume.")

    if not fed:
        st.warning("No federation results. Run `python src/federated/fedavg.py`.")
    else:
        fdf = pd.DataFrame(fed)

        f = go.Figure()
        f.add_bar(x=fdf.node, y=fdf.local_mape, name="Trained alone",
                  marker_color="#DC2626")
        f.add_bar(x=fdf.node, y=fdf.federated_mape, name="With federation",
                  marker_color="#10B981")
        f.update_layout(barmode="group", height=380,
                        yaxis_title="Forecast error (MAPE %)",
                        margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(f, use_container_width=True)

        st.dataframe(fdf, use_container_width=True, hide_index=True)

        best = fdf.loc[fdf["improvement_%"].idxmax()]
        st.success(
            f"**{best['node']}** has only {int(best['train_rows']):,} training rows "
            f"— too little to learn monsoon seasonality alone. Federation reduces "
            f"its forecast error from {best['local_mape']}% to "
            f"{best['federated_mape']}% ({best['improvement_%']}% better), "
            f"without a single data row leaving the node.")

        st.markdown("""
**What crosses a node boundary:** model coefficients and feature statistics only.
**What never leaves:** inventory records, patient counts, facility data.

The gain scales inversely with local data volume — data-rich nodes are unaffected,
data-poor nodes benefit most, and nobody is made worse off. That monotonic
relationship is the theoretical prediction for federated averaging, and it holds
here: seasonality is shared structure, so it can be learned collectively without
pooling the underlying data.
""")

# ---------------------------------------------------------------- resilience
with tab6:
    st.subheader("PHC Resilience Score")
    st.caption("One score per facility, combining medicine availability (40%), "
               "stock-out urgency (20%), staff availability (20%) and bed "
               "headroom (20%). Ranked so a district officer knows where to "
               "intervene first, rather than reading four separate tables.")

    b1, b2, b3, b4 = st.columns(4)
    for col, name in zip([b1, b2, b3, b4],
                         ["HIGH RISK", "AT RISK", "STABLE", "RESILIENT"]):
        col.metric(name.title(), int((resil.band == name).sum()))

    st.divider()

    # ---- the worst facility, explained ---------------------------------
    w = resil.iloc[0]
    st.markdown(f"### Most vulnerable: {w.facility_name}")

    s1, s2 = st.columns([1, 2])
    with s1:
        st.markdown(
            f"<div style='text-align:center;padding:18px;border-radius:10px;"
            f"background:{BAND_COLOR[w.band]}22;"
            f"border:2px solid {BAND_COLOR[w.band]}'>"
            f"<div style='font-size:52px;font-weight:700;"
            f"color:{BAND_COLOR[w.band]}'>{int(w.score)}</div>"
            f"<div style='font-size:13px;opacity:.7'>out of 100</div>"
            f"<div style='font-size:17px;font-weight:600;margin-top:6px;"
            f"color:{BAND_COLOR[w.band]}'>{w.band}</div></div>",
            unsafe_allow_html=True)

    with s2:
        factors = pd.DataFrame({
            "Factor": ["Medicine availability", "Stock-out urgency",
                       "Staff availability", "Bed headroom"],
            "Score": [w.supply_pct, w.urgency_pct, w.staffing_pct, w.capacity_pct],
        })
        fg = go.Figure()
        fg.add_bar(x=factors.Score, y=factors.Factor, orientation="h",
                   marker_color=["#DC2626" if v < 50 else
                                 "#F59E0B" if v < 75 else "#10B981"
                                 for v in factors.Score],
                   text=[f"{v:.0f}%" for v in factors.Score],
                   textposition="outside")
        fg.update_layout(height=210, xaxis_range=[0, 115],
                         margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
        st.plotly_chart(fg, use_container_width=True)

    st.error(
        f"**Primary risk:** {w.primary_risk} — "
        f"{'already at zero' if w.days_to_next_stockout == 0 else f'{w.days_to_next_stockout:.1f} days to stock-out'}  \n"
        f"**Weakest factor:** {w.weakest_factor}  \n"
        f"**Supply status:** {int(w.skus_stocked_out)} of {int(w.skus_total)} "
        f"medicines already at zero, {int(w.skus_critical)} more running out")

    st.divider()

    # ---- ranked list ----------------------------------------------------
    st.markdown("#### All facilities, ranked by vulnerability")

    fig = go.Figure()
    for bnd in ["HIGH RISK", "AT RISK", "STABLE", "RESILIENT"]:
        sub = resil[resil.band == bnd]
        if len(sub):
            fig.add_bar(x=sub.score, y=sub.facility_name, orientation="h",
                        name=bnd, marker_color=BAND_COLOR[bnd],
                        hovertemplate="<b>%{y}</b><br>score %{x}<extra></extra>")
    fig.update_layout(height=760, barmode="stack",
                      xaxis_title="Resilience score (0–100)",
                      yaxis=dict(autorange="reversed"),
                      margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Score breakdown, all facilities"):
        st.dataframe(
            resil[["facility_name", "facility_type", "district", "score", "band",
                   "supply_pct", "urgency_pct", "staffing_pct", "capacity_pct",
                   "skus_stocked_out", "primary_risk"]],
            use_container_width=True, hide_index=True, height=380)

    with st.expander("Bed and staff detail"):
        st.dataframe(
            status[["facility_name", "facility_type", "district",
                    "beds_occupied", "beds_sanctioned", "occupancy_pct",
                    "doctors_present", "doctors_sanctioned",
                    "nurses_present", "nurses_sanctioned",
                    "pharmacists_present", "pharmacists_sanctioned",
                    "staff_present_pct"]],
            use_container_width=True, hide_index=True, height=340)

    st.warning(
        "**Data note.** Bed occupancy and staff attendance are generated against "
        "Indian Public Health Standards norms — 6 beds and 2 doctors per PHC, "
        "30 beds and 6 doctors per CHC — with vacancy correlated to each "
        "facility's supply stress. No public API exposes either live. The scoring "
        "logic operates identically on real HMIS attendance data.")

# ---------------------------------------------------------------- evidence
with tab7:
    st.subheader("How this data was constructed")
    st.caption("Live PHC inventory APIs are not publicly available in India. "
               "Rather than generating random numbers, consumption is computed "
               "from district disease incidence through published clinical "
               "treatment courses. Here is exactly how, and what that does "
               "and does not prove.")

    d = st.selectbox("District", sorted(disease.district.unique()))

    ors = ledger[(ledger.district == d) & (ledger.sku_code == "ORS001")].copy()
    ors["month"] = ors.date.dt.to_period("M").astype(str)
    om = ors.groupby("month").issues.sum()

    dia = disease[(disease.district == d) &
                  (disease.disease == "diarrhoeal")].copy()
    dia["month"] = dia.week_start.dt.to_period("M").astype(str)
    dm = dia.groupby("month").case_count.sum()

    comp = pd.DataFrame({"Diarrhoeal cases": dm, "ORS issued": om}).dropna()

    f = go.Figure()
    f.add_scatter(x=comp.index, y=comp["Diarrhoeal cases"],
                  name="Diarrhoeal cases", line=dict(color="#DC2626", width=2))
    f.add_scatter(x=comp.index, y=comp["ORS issued"], name="ORS issued",
                  yaxis="y2", line=dict(color="#2563EB", width=2))
    f.update_layout(height=340, yaxis2=dict(overlaying="y", side="right"),
                    margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(f, use_container_width=True)

    r = comp.iloc[:, 0].corr(comp.iloc[:, 1])
    m1, m2 = st.columns([1, 3])
    m1.metric("Correlation", f"{r:.3f}")
    m2.warning(
        "**This correlation is expected, not discovered.** ORS consumption was "
        "*derived* from diarrhoeal case counts at 6 sachets per case, so the two "
        "series are related by construction. The chart confirms the generator "
        "applies clinical norms consistently across 18 months and three districts "
        "— it is a validation of the construction, not evidence that the data "
        "matches real PHC records.")

    st.markdown("""
#### What is real

- **District structure** — Nalgonda, Yadadri Bhuvanagiri and Suryapet are real
  Telangana districts. Facility counts follow Indian Public Health Standards:
  1 PHC per ~30,000 rural population, 1 CHC per ~120,000.
- **Medicine list** — drawn from the National List of Essential Medicines.
- **Diarrhoeal incidence and treatment rates** — calibrated against NFHS-5
  (2019–21) measured values for Telangana: 5.46% two-week prevalence in
  under-5s, 61.8% receiving ORS, 39.3% receiving zinc, and 71.1% of cases
  reaching a health provider. Source file included in `data/raw/`.
- **Clinical consumption norms** — ORS at 6 sachets per diarrhoeal case,
  artemether-lumefantrine at 1 course per malaria case, and so on, from
  standard treatment guidelines.

#### What is modelled

- **Seasonal shape** — monsoon-driven peaks in diarrhoeal, cholera and malaria
  incidence, modelled on published IDSP seasonal patterns for south Indian
  districts rather than downloaded week by week.

#### What is synthesised

- **Stock levels, receipts and issues.** No public API exposes live PHC
  inventory. These are computed forward from disease incidence through the
  clinical norms above, with procurement modelled as a 30-day indent cycle,
  7–21 day lead times, and probabilistic delivery delays that differ by district.
- **Bed occupancy and staff attendance**, generated against IPHS norms.

#### What this does not claim

This data is **structurally plausible, not empirically validated**. It reproduces
the shape of the problem — monsoon demand spikes, indent-cycle sawtooth patterns,
chronic under-supply in specific districts — but the specific numbers are not
measurements of any real facility.

#### Point-in-time correctness

IDSP surveillance is published weekly, in arrears. A forecast made on a Tuesday
cannot use that week's completed case count. All disease features are therefore
lagged by at least one full week, and the weekly series is shifted before joining
to daily records — so no same-week value can leak into the feature matrix. This
costs accuracy, and that is the point: the reported figures are what the system
would achieve in production.

#### Why that is sufficient for this prototype

The system's value is in the pipeline, not the numbers: forecasting from disease
surveillance, converting forecasts to reorder decisions, solving redistribution
under constraints, and federating models without pooling data. Every one of those
operates identically on real DVDMS records.

The ingestion schema (`docs/openapi.yaml`) specifies how DVDMS-shaped records
enter the system. A state connects its live export at that interface and the
synthetic layer is replaced — nothing downstream changes. The endpoints are
specified but not yet implemented.
""")