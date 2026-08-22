"""AarogyaGrid — dashboard."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.gemini.nl_query import run as nl_run, build_frame
st.set_page_config(page_title="AarogyaGrid", page_icon="🏥", layout="wide")

OUT = "data/processed"


@st.cache_data
def load(v="3"):
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

    # Parquet can restore these as object dtype on a fresh container,
    # which breaks the .dt accessor. Coerce explicitly.
    disease["week_start"] = pd.to_datetime(disease["week_start"], errors="coerce")
    ledger["date"]        = pd.to_datetime(ledger["date"], errors="coerce")

    return alerts, transfers, disease, ledger, briefs, fed, status


alerts, transfers, disease, ledger, briefs, fed, status = load("3")

TIER_COLOR = {"STOCKOUT": "#8B0000", "CRITICAL": "#DC2626",
              "WARNING": "#F59E0B", "WATCH": "#FCD34D", "OK": "#10B981"}

st.title("AarogyaGrid")
st.caption("Predictive stock-out prevention for India's primary health network — "
           "a forecasting and redistribution layer above existing DVDMS/e-Aushadhi systems")

# ---------------------------------------------------------------- KPIs
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Facilities monitored", alerts.facility_id.nunique())
c2.metric("Already stocked out", int((alerts.tier == "STOCKOUT").sum()),
          help="Failures that early warning would have prevented")
c3.metric("Preventable stock-outs", int((alerts.tier == "CRITICAL").sum()),
          help="Stock remains, but will deplete before resupply")
c4.metric("Transfer orders", len(transfers))
c5.metric("Courses protected", f"{int(transfers.courses_covered.sum()):,}")

st.divider()
# ---------------------------------------------------------------- NL query
with st.expander("🔍 **Ask a question** — natural language search across all facilities", expanded=False):
    st.caption("Gemini translates your question into a query over the facility "
               "data. Try: *understaffed facilities in Yadadri running out of "
               "antimalarials* · *facilities at bed capacity that are also "
               "running out of medicine* · *which PHCs are already out of ORS*")

    q = st.text_input("Question", placeholder="e.g. which CHCs are running out of antibiotics?",
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
            from src.gemini.nl_query import summarise
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
     "AI Briefings", "Federated Learning", "Facility Capacity", "Why It Works"])

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
                            show.apply(lambda r: f"{r.facility_name} — {r.sku_name}", axis=1))
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
    st.caption(f"{len(transfers)} orders · {int(transfers.cross_district.sum())} cross-district · "
               f"{int(transfers.quantity.sum()):,} units · mean {transfers.road_km.mean():.0f} km")

    for r in transfers.head(12).itertuples():
        with st.container(border=True):
            a, b = st.columns([3, 1])
            a.markdown(
                f"**Move {r.quantity:,} × {r.sku_name}**  \n"
                f"FROM **{r.from_facility}** ({r.from_district}) — {r.from_surplus_units:,} surplus units  \n"
                f"TO **{r.to_facility}** ({r.to_district}) — "
                f"{'already at zero' if r.to_days_to_stockout == 0 else f'{r.to_days_to_stockout} days to stock-out'}")
            b.metric("Distance", f"{r.road_km} km", f"~{r.drive_min} min")
            b.caption(f"{int(r.courses_covered)} treatment courses")

# ---------------------------------------------------------------- AI briefs
with tab4:
    st.subheader("Gemini-generated field briefings")
    st.caption("Each alert is converted into a causal explanation an officer "
               "can act on, and translated for the PHC pharmacist. Generated "
               "with Gemini and cached — no live API call on page load.")

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
    st.subheader("Federated learning across states")
    st.caption("Each state trains on its own data. Only model coefficients and "
               "feature statistics are exchanged — no inventory records, no "
               "patient data, no facility rows cross a state boundary.")

    st.info(
        "**How these nodes are constructed.** The three nodes are simulated by "
        "partitioning our districts and giving each a deliberately different "
        "amount of training history — 18, 9 and 3 months. They carry state names "
        "to make the scenario legible, but the underlying facilities are in "
        "Telangana. What is being demonstrated is the *federation mechanism*, "
        "which is identical regardless of how nodes are partitioned: each node "
        "trains locally, shares only weights, and receives a blended model "
        "weighted by its own data volume.")

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
            f"without a single data row leaving the state.")

        st.markdown("""
**What crosses a state boundary:** 12 model coefficients, 12 feature statistics.
**What never leaves the state:** inventory records, patient counts, facility data.

The gain scales inversely with local data volume — data-rich states are unaffected,
data-poor states benefit most. Seasonality is shared structure across states, so it
can be learned collectively without pooling the underlying data.
""")

# ---------------------------------------------------------------- capacity
with tab6:
    st.subheader("Bed availability and staff attendance")
    st.caption("The problem statement asks for visibility into beds and personnel "
               "alongside medicine stock. Both arrive through the same ingestion "
               "schema as inventory — this view demonstrates that interface.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Mean bed occupancy", f"{status.occupancy_pct.mean():.0f}%")
    k2.metric("Above 85% occupancy", int((status.occupancy_pct > 85).sum()),
              help="Facilities near or at bed capacity")
    k3.metric("Mean staff present", f"{status.staff_present_pct.mean():.0f}%")
    k4.metric("Below 70% staffed", int((status.staff_present_pct < 70).sum()),
              help="Facilities operating well below sanctioned strength")

    st.divider()

    both = status[(status.staff_present_pct < 80) & (status.supply_stressed_skus >= 3)]
    if len(both):
        st.error(
            f"**{len(both)} facilities are simultaneously understaffed and "
            f"supply-stressed.** These are the sites where a stock-out does the "
            f"most damage — fewer staff to manage rationing, referral, or "
            f"emergency indents. District planning should prioritise them.")
        st.dataframe(
            both[["facility_name", "district", "occupancy_pct",
                  "staff_present_pct", "supply_stressed_skus"]]
            .sort_values("supply_stressed_skus", ascending=False),
            use_container_width=True, hide_index=True)

    st.divider()

    f = go.Figure()
    f.add_scatter(
        x=status.staff_present_pct, y=status.occupancy_pct,
        mode="markers", text=status.facility_name,
        marker=dict(size=status.supply_stressed_skus * 4 + 8,
                    color=status.supply_stressed_skus,
                    colorscale="Reds", showscale=True,
                    colorbar=dict(title="Stressed<br>SKUs")),
        hovertemplate="<b>%{text}</b><br>staff %{x}%<br>beds %{y}%<extra></extra>")
    f.add_vline(x=70, line_dash="dash", line_color="#F59E0B",
                annotation_text="70% staffed")
    f.add_hline(y=85, line_dash="dash", line_color="#F59E0B",
                annotation_text="85% occupancy")
    f.update_layout(height=420, xaxis_title="Staff present (% of sanctioned)",
                    yaxis_title="Bed occupancy (%)",
                    margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(f, use_container_width=True)

    with st.expander("Full facility table"):
        st.dataframe(
            status[["facility_name", "facility_type", "district",
                    "beds_occupied", "beds_sanctioned", "occupancy_pct",
                    "doctors_present", "doctors_sanctioned",
                    "nurses_present", "nurses_sanctioned",
                    "staff_present_pct"]],
            use_container_width=True, hide_index=True, height=340)

    st.warning(
        "**Data note.** No public API exposes live bed occupancy or staff "
        "attendance for Indian PHCs. These figures are generated against Indian "
        "Public Health Standards (IPHS) norms — 6 beds and 2 doctors per PHC, "
        "30 beds and 6 doctors per CHC — with occupancy and vacancy correlated "
        "to each facility's supply stress. The purpose is to demonstrate the "
        "ingestion interface these fields arrive through, not to report real "
        "occupancy.")

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

    dia = disease[(disease.district == d) & (disease.disease == "diarrhoeal")].copy()
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
  Telangana districts. Facility counts follow Indian norms: 1 PHC per ~30,000
  rural population, 1 CHC per ~120,000.
- **Medicine list** — drawn from the National List of Essential Medicines.
- **Clinical consumption norms** — ORS at 6 sachets per diarrhoeal case,
  artemether-lumefantrine at 1 course per malaria case, and so on. These come
  from standard treatment guidelines.
- **Seasonal shape** — monsoon-driven peaks in diarrhoeal, cholera and malaria
  incidence, modelled on published IDSP seasonal patterns for south Indian
  districts.

#### What is synthesised

- **Stock levels, receipts and issues.** No public API exposes live PHC
  inventory. These are computed forward from disease incidence through the
  clinical norms above, with procurement modelled as a 30-day indent cycle,
  7–21 day lead times, and probabilistic delivery delays that differ by district.

#### What this does not claim

This data is **structurally plausible, not empirically validated**. It reproduces
the shape of the problem — monsoon demand spikes, indent-cycle sawtooth patterns,
chronic under-supply in some districts — but the specific numbers are not
measurements of any real facility.

#### Why that is sufficient for this prototype

The system's value is in the pipeline, not the numbers: forecasting from disease
surveillance, converting forecasts to reorder decisions, solving redistribution
under constraints, and federating models without pooling data. Every one of those
operates identically on real DVDMS records.

The ingestion API (`docs/openapi.yaml`) accepts DVDMS-shaped records. A state
connects its live export and the synthetic layer is replaced — nothing else in
the system changes.
""")