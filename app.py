"""AarogyaGrid — dashboard."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="AarogyaGrid", page_icon="🏥", layout="wide")

OUT = "data/processed"

@st.cache_data
def load():
    import json, os
    briefs, fed = {}, []
    if os.path.exists(f"{OUT}/briefs.json"):
        briefs = json.load(open(f"{OUT}/briefs.json", encoding="utf-8"))
    if os.path.exists(f"{OUT}/federation.json"):
        fed = json.load(open(f"{OUT}/federation.json", encoding="utf-8"))
    return (pd.read_parquet(f"{OUT}/alerts.parquet"),
            pd.read_parquet(f"{OUT}/transfers.parquet"),
            pd.read_parquet(f"{OUT}/disease_weekly.parquet"),
            pd.read_parquet(f"{OUT}/stock_ledger.parquet"),
            briefs, fed)


alerts, transfers, disease, ledger, briefs, fed = load()

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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Alert Map", "Preventable Stock-outs", "Redistribution Plan",
     "AI Briefings", "Federated Learning", "Why It Works"])

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
              "daily_burn", "days_to_stockout", "reorder_point", "disease_trend"]],
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
                f"**{row.days_to_stockout} days**. District disease activity is at "
                f"**{row.disease_trend}x** its 28-day norm.")

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