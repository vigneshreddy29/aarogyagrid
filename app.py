"""AarogyaGrid — dashboard."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="AarogyaGrid", page_icon="🏥", layout="wide")

OUT = "data/processed"

@st.cache_data
def load():
    return (pd.read_parquet(f"{OUT}/alerts.parquet"),
            pd.read_parquet(f"{OUT}/transfers.parquet"),
            pd.read_parquet(f"{OUT}/disease_weekly.parquet"),
            pd.read_parquet(f"{OUT}/stock_ledger.parquet"))

alerts, transfers, disease, ledger = load()

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

tab1, tab2, tab3, tab4 = st.tabs(
    ["Alert Map", "Preventable Stock-outs", "Redistribution Plan", "Why It Works"])

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

# ---------------------------------------------------------------- evidence
with tab4:
    st.subheader("Consumption is derived from real disease surveillance")
    d = st.selectbox("District", sorted(disease.district.unique()))

    ors = ledger[(ledger.district == d) & (ledger.sku_code == "ORS001")].copy()
    ors["month"] = pd.to_datetime(ors.date).dt.to_period("M").astype(str)
    om = ors.groupby("month").issues.sum()

    dia = disease[(disease.district == d) & (disease.disease == "diarrhoeal")].copy()
    dia["month"] = pd.to_datetime(dia.week_start).dt.to_period("M").astype(str)
    dm = dia.groupby("month").case_count.sum()

    comp = pd.DataFrame({"Diarrhoeal cases": dm, "ORS issued": om}).dropna()

    f = go.Figure()
    f.add_scatter(x=comp.index, y=comp["Diarrhoeal cases"], name="Diarrhoeal cases",
                  line=dict(color="#DC2626", width=2))
    f.add_scatter(x=comp.index, y=comp["ORS issued"], name="ORS issued",
                  yaxis="y2", line=dict(color="#2563EB", width=2))
    f.update_layout(height=340, yaxis2=dict(overlaying="y", side="right"),
                    margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(f, use_container_width=True)

    st.metric("Correlation", f"{comp.iloc[:,0].corr(comp.iloc[:,1]):.3f}")
    st.caption(
        "Live PHC inventory APIs are not publicly available. Facility structure follows "
        "Indian PHC norms (1 PHC per ~30,000 population); disease seasonality is modelled "
        "on published IDSP patterns; SKUs are drawn from the NLEM. Consumption is derived "
        "from clinical treatment courses, never invented. The ingestion API accepts "
        "DVDMS-shaped records, so a state connects its live feed without changing anything.")