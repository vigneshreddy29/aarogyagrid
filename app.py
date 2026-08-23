"""AarogyaGrid — dashboard."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import style

from src.gemini.nl_query import (run as nl_run, summarise, route,
                                 situation, advise, explain,
                                 translate, LANGUAGES)

st.set_page_config(page_title="AarogyaGrid", page_icon="🏥", layout="wide")
style.apply(st)

OUT = "data/processed"
LEAD_TIME_NOTE = "typical resupply lead time is 7–21 days"


@st.cache_data
def load(v="6"):
    import json

    briefs, fed, scen = {}, [], []
    if os.path.exists(f"{OUT}/briefs.json"):
        briefs = json.load(open(f"{OUT}/briefs.json", encoding="utf-8"))
    if os.path.exists(f"{OUT}/federation.json"):
        fed = json.load(open(f"{OUT}/federation.json", encoding="utf-8"))
    if os.path.exists(f"{OUT}/scenarios.json"):
        scen = json.load(open(f"{OUT}/scenarios.json", encoding="utf-8"))

    alerts    = pd.read_parquet(f"{OUT}/alerts.parquet")
    transfers = pd.read_parquet(f"{OUT}/transfers.parquet")
    disease   = pd.read_parquet(f"{OUT}/disease_weekly.parquet")
    ledger    = pd.read_parquet(f"{OUT}/stock_ledger.parquet")
    status    = pd.read_parquet(f"{OUT}/facility_status.parquet")
    resil     = pd.read_parquet(f"{OUT}/resilience.parquet")
    foot      = pd.read_parquet(f"{OUT}/footfall.parquet")
    link      = pd.read_parquet(f"{OUT}/footfall_link.parquet")

    disease["week_start"] = pd.to_datetime(disease["week_start"], errors="coerce")
    ledger["date"]        = pd.to_datetime(ledger["date"], errors="coerce")
    foot["date"]          = pd.to_datetime(foot["date"], errors="coerce")

    return (alerts, transfers, disease, ledger, briefs, fed,
            status, resil, foot, link, scen)


(alerts, transfers, disease, ledger, briefs, fed,
 status, resil, foot, link, scen) = load("6")


@st.cache_data(show_spinner=False)
def T(text, lang):
    """Translate once per unique string per language. English is a no-op."""
    return translate(text, lang) if lang else text


TIER_COLOR = {"STOCKOUT": "#8B0000", "CRITICAL": "#F43F5E",
              "WARNING": "#FBBF24", "WATCH": "#FCD34D", "OK": "#34D399"}

BAND_COLOR = {"HIGH RISK": "#F43F5E", "AT RISK": "#FBBF24",
              "STABLE": "#A3E635", "RESILIENT": "#34D399"}

# ==================================================================== header

st.title("AarogyaGrid")
st.caption("Predictive stock-out prevention for India's primary health network — "
           "a forecasting and redistribution layer above existing "
           "DVDMS/e-Aushadhi systems")
st.caption("**Prototype coverage:** Telangana — 3 districts, 37 facilities. "
           "The architecture is state → district → facility, so additional "
           "states connect as additional nodes. The demonstration data is "
           "not national.")

lang_label = st.radio(
    "Language", list(LANGUAGES.keys()), index=0, horizontal=True,
    label_visibility="collapsed")
LANG = LANGUAGES[lang_label]

if LANG:
    st.success(
        f"**{lang_label}** — operational content is delivered in this language: "
        f"AI briefings, recommendations, alert explanations and transfer "
        f"orders. Navigation labels and data tables remain in English, since "
        f"district reporting and stock registers are maintained in English. "
        f"Medicine and facility names are never translated, so they match the "
        f"packaging.")

# ---------------------------------------------------------------- KPIs
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Facilities monitored", alerts.facility_id.nunique())
c2.metric("High risk facilities", int((resil.band == "HIGH RISK").sum()),
          help="Resilience index below 50 — supply, staffing and capacity combined")
c3.metric("Already stocked out", int((alerts.tier == "STOCKOUT").sum()),
          help="Failures that early warning would have prevented")
c4.metric("Preventable stock-outs", int((alerts.tier == "CRITICAL").sum()),
          help="Stock remains, but will deplete before resupply")
c5.metric("Courses protected", f"{int(transfers.courses_covered.sum()):,}")

st.divider()

w0 = resil.iloc[0]
style.ribbon(st, w0.facility_name, int(w0.score), w0.band,
             w0.primary_risk, w0.days_to_next_stockout, w0.district)

# ==================================================================== chat

SUGGESTIONS = [
    "Which PHCs are already out of ORS?",
    "What should the district prioritise this week?",
    "Why is Yadadri Bhuvanagiri failing?",
    "How does the forecast work?",
]

if "chat" not in st.session_state:
    st.session_state.chat = []
if "pending_q" not in st.session_state:
    st.session_state.pending_q = None

with st.expander("💬 **Ask AarogyaGrid** — ask about stock, priorities, or how "
                 "the system works", expanded=False):

    st.caption("Questions are routed three ways: a data filter returns matching "
               "facilities, an advice question returns a briefing grounded in "
               "the live figures, and a system question explains how the "
               "forecast, index or federation works.")

    sc = st.columns(len(SUGGESTIONS))
    for i, s in enumerate(SUGGESTIONS):
        if sc[i].button(s, key=f"sg_{i}", use_container_width=True):
            st.session_state.pending_q = s
            st.rerun()

    with st.form("nlq", clear_on_submit=True):
        fc1, fc2 = st.columns([6, 1])
        typed = fc1.text_input(
            "Question", label_visibility="collapsed",
            placeholder="e.g. which CHCs are running out of antibiotics?")
        submitted = fc2.form_submit_button("Ask", use_container_width=True)

    q = st.session_state.pending_q or (typed if submitted and typed else None)
    st.session_state.pending_q = None

    if q:
        with st.spinner("Thinking…"):
            try:
                mode = route(q)
            except Exception:
                mode = "FILTER"

        entry = {"q": q, "mode": mode, "expr": None, "err": None,
                 "n": 0, "brief": "", "answer": ""}

        if mode == "ADVISE":
            entry["answer"] = advise(
                q, situation(alerts, resil, transfers, status, scen))

        elif mode == "EXPLAIN":
            entry["answer"] = explain(q)

        elif mode == "OTHER":
            entry["err"] = ("I answer questions about this facility network — "
                            "stock levels, which facilities are at risk, what "
                            "the district should prioritise, or how the system "
                            "works. Try one of the suggestions above.")
        else:
            try:
                res, expr, err = nl_run(q)
            except Exception as e:
                res, expr, err = None, None, str(e)
            entry["expr"], entry["err"] = expr, err
            if res is not None and len(res):
                entry["n"] = len(res)
                try:
                    entry["brief"] = summarise(q, res)
                except Exception:
                    pass
                entry["rows"] = res[["facility_name", "facility_type", "district",
                                     "sku_name", "current_stock",
                                     "days_to_stockout", "tier",
                                     "occupancy_pct", "staff_present_pct"]]

        if LANG:
            with st.spinner("Translating…"):
                entry["answer"] = T(entry["answer"], LANG)
                entry["brief"] = T(entry["brief"], LANG)

        st.session_state.chat.insert(0, entry)

    if st.session_state.chat:
        if st.button("Clear history", key="clr"):
            st.session_state.chat = []
            st.rerun()

        for e in st.session_state.chat:
            with st.container(border=True):
                st.markdown(f"**❯ {e['q']}**")
                st.caption(f"mode: {e.get('mode', 'FILTER')}")

                if e.get("answer"):
                    st.success(e["answer"])

                if e["err"]:
                    st.warning(e["err"])
                elif e.get("mode") in ("ADVISE", "EXPLAIN"):
                    pass
                elif e["n"] == 0:
                    st.info("No facilities match that query.")
                else:
                    if e["brief"]:
                        st.info(e["brief"])
                    st.caption(f"{e['n']} matching facility-medicine pairs")
                    st.dataframe(e["rows"], use_container_width=True,
                                 hide_index=True, height=240)

                if e["expr"]:
                    with st.expander("Query Gemini generated", expanded=False):
                        st.code(e["expr"], language="python")
                        st.caption("Validated against a blocklist before "
                                   "execution — only read operations on the "
                                   "in-memory dataframe are permitted.")

st.divider()

# ==================================================================== tabs

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
    ["Alert Map", "Patient Footfall", "Emergency Mode", "Preventable Stock-outs",
     "Redistribution Plan", "AI Briefings", "Federated Learning",
     "PHC Resilience Index", "Why It Works"])

# ---------------------------------------------------------------- map
with tab1:
    risk_by_district = (alerts[alerts.tier.isin(["STOCKOUT", "CRITICAL"])]
                        .groupby("district").size().sort_values(ascending=False))
    top_d = risk_by_district.index[0]

    st.info(T(
        f"**How to read this map.** Each pin is a facility, sized by the "
        f"population it serves and coloured by its worst medicine status. "
        f"**{int(risk_by_district.iloc[0])} of {int(risk_by_district.sum())} "
        f"at-risk facility-medicine pairs are concentrated in {top_d}** — the "
        f"red cluster. The green facilities are fully stocked, which is "
        f"precisely what makes redistribution possible: surplus exists "
        f"{int(transfers.road_km.mean())} km away, on average, from where it "
        f"is needed.\n\n"
        f"Every colour here is a **forecast, not a reading**. A facility is red "
        f"because its projected burn rate empties the shelf before the next "
        f"resupply arrives — not because it is empty today. "
        f"{int((alerts.tier == 'STOCKOUT').sum())} pairs are already at zero; "
        f"the other {int((alerts.tier == 'CRITICAL').sum())} are still "
        f"preventable.", LANG))

    worst = (alerts.assign(rank=alerts.tier.map(
                {"STOCKOUT": 0, "CRITICAL": 1, "WARNING": 2,
                 "WATCH": 3, "OK": 4}))
             .sort_values("rank").groupby("facility_id", as_index=False).first())

    fig = px.scatter_map(
        worst, lat="latitude", lon="longitude", color="tier",
        color_discrete_map=TIER_COLOR, size="catchment_population",
        size_max=22, zoom=7.2, height=520,
        hover_name="facility_name",
        hover_data={"district": True, "sku_name": True,
                    "days_to_stockout": True,
                    "latitude": False, "longitude": False},
        map_style="carto-darkmatter")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(style.dark(fig), use_container_width=True)

    st.dataframe(alerts.tier.value_counts().rename("facility-SKU pairs"),
                 use_container_width=True)

# ---------------------------------------------------------------- footfall
with tab2:
    st.subheader("Patient footfall → demand signal → medicine need")
    st.caption("Footfall is the operational link between disease in the "
               "community and stock leaving a shelf. A case only consumes "
               "medicine once the patient walks in.")

    latest = foot.date.max()
    today = foot[foot.date == latest]

    f1, f2, f3, f4, f5 = st.columns(5)
    f1.metric("OPD visits today", f"{int(today.opd_visits.sum()):,}")
    f2.metric("IPD admissions", int(today.ipd_admissions.sum()))
    f3.metric("Emergency cases", int(today.emergency_cases.sum()))
    f4.metric("Referrals", int(today.referrals.sum()))
    f5.metric("Mean wait", f"{today.avg_wait_min.mean():.0f} min")

    st.divider()

    rising = today.nlargest(1, "opd_trend_pct").iloc[0]
    fac_alerts = alerts[(alerts.facility_id == rising.facility_id) &
                        (alerts.tier.isin(["CRITICAL", "STOCKOUT"]))]

    if len(fac_alerts):
        a = fac_alerts.nsmallest(1, "days_to_stockout").iloc[0]
        chain = (f"**{rising.facility_name}** — OPD up "
                 f"**{rising.opd_trend_pct:+.1f}%** week on week "
                 f"({int(rising.opd_visits)} visits today) → "
                 f"**{a.sku_name}** burning {a.daily_burn}/day → "
                 f"stock-out in **{a.days_to_stockout:.1f} days**")
    else:
        chain = (f"**{rising.facility_name}** — OPD up "
                 f"**{rising.opd_trend_pct:+.1f}%** week on week "
                 f"({int(rising.opd_visits)} visits today). No medicine at risk "
                 f"yet; the forecaster is tracking it.")
    st.warning(T(chain, LANG))

    st.divider()

    pick = st.selectbox("Facility", sorted(foot.facility_name.unique()),
                        key="foot_pick")
    h = foot[foot.facility_name == pick].tail(120)

    ff = go.Figure()
    ff.add_bar(x=h.date, y=h.opd_visits, name="OPD visits",
               marker_color="rgba(91,141,239,0.40)")
    ff.add_scatter(x=h.date, y=h.opd_7d, name="7-day average",
                   line=dict(color="#5B8DEF", width=2.5))
    ff.add_scatter(x=h.date, y=h.emergency_cases, name="Emergency",
                   line=dict(color="#F43F5E", width=1.8))
    ff.update_layout(height=330, yaxis_title="Patients")
    st.plotly_chart(style.dark(ff), use_container_width=True)

    st.markdown("#### Does footfall actually move medicine?")

    r1, r2 = st.columns([1, 2])
    r1.metric("Median correlation", f"{link.footfall_demand_r.median():.3f}",
              help="Weekly OPD volume vs units issued, per facility")
    r1.metric("Facilities above 0.5",
              f"{int((link.footfall_demand_r > 0.5).sum())} of {len(link)}")

    with r2:
        hist = go.Figure()
        hist.add_histogram(x=link.footfall_demand_r, nbinsx=16,
                           marker_color="rgba(52,211,153,0.65)")
        hist.update_layout(height=210, xaxis_title="Correlation (r)",
                           yaxis_title="Facilities")
        st.plotly_chart(style.dark(hist), use_container_width=True)

    st.info(T(
        "**Measured weekly, and only on days stock was available.** A facility "
        "that has run out issues nothing no matter how many patients arrive — "
        "including those days would mask the relationship rather than measure "
        "it. Daily figures are also too noisy in both series; weekly "
        "aggregation is the honest window.", LANG))

    with st.expander("Footfall by facility, today"):
        st.dataframe(
            today[["facility_name", "facility_type", "district", "opd_visits",
                   "opd_7d", "opd_trend_pct", "ipd_admissions",
                   "emergency_cases", "referrals", "avg_wait_min"]]
            .sort_values("opd_visits", ascending=False).round(1),
            use_container_width=True, hide_index=True, height=340)

# ---------------------------------------------------------------- emergency
with tab3:
    st.subheader("Emergency mode — what happens when demand surges")
    st.caption("The challenge asks for early warning during health emergencies. "
               "A steady-state forecast cannot answer that. Each scenario "
               "applies disease-specific demand multipliers and re-runs the "
               "same reorder arithmetic — nothing is retrained, which is "
               "exactly what would happen in production.")

    if not scen:
        st.warning("Run `python src/alerts/emergency.py`.")
    else:
        sdf = pd.DataFrame(scen)
        spick = st.radio("Scenario", sdf.scenario.tolist(),
                         horizontal=True, key="scen_pick")
        s = sdf[sdf.scenario == spick].iloc[0]

        st.info(T(s.note, LANG))

        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Facilities at risk", int(s.surge_at_risk),
                  delta=f"+{int(s.surge_at_risk - s.baseline_at_risk)} vs normal",
                  delta_color="inverse")
        e2.metric("Newly critical", int(s.newly_at_risk),
                  help="Facilities that were coping and now are not")
        e3.metric("Warning time lost", f"{s.median_days_lost:.1f} d",
                  help="Median reduction in days-to-stock-out")
        e4.metric("Fail inside onset window", int(s.fail_before_onset),
                  help=f"Deplete within the {int(s.onset_days)}-day onset period")

        st.divider()

        fname = f"{OUT}/surge_{spick.split()[0].lower()}.parquet"
        if os.path.exists(fname):
            sd = pd.read_parquet(fname)
            aff = sd[sd.surge_mult > 1].copy()

            cmp = pd.DataFrame({
                "state": ["Normal", spick],
                "STOCKOUT": [int((sd.tier == "STOCKOUT").sum()),
                             int((sd.surge_tier == "STOCKOUT").sum())],
                "CRITICAL": [int((sd.tier == "CRITICAL").sum()),
                             int((sd.surge_tier == "CRITICAL").sum())],
                "WARNING":  [int((sd.tier == "WARNING").sum()),
                             int((sd.surge_tier == "WARNING").sum())],
                "OK":       [int((sd.tier == "OK").sum()),
                             int((sd.surge_tier == "OK").sum())],
            })

            cf = go.Figure()
            for tname, col in [("OK", "#34D399"), ("WARNING", "#FBBF24"),
                               ("CRITICAL", "#F43F5E"), ("STOCKOUT", "#8B0000")]:
                cf.add_bar(x=cmp.state, y=cmp[tname], name=tname,
                           marker_color=col)
            cf.update_layout(barmode="stack", height=330,
                             yaxis_title="Facility-medicine pairs")
            st.plotly_chart(style.dark(cf), use_container_width=True)

            st.markdown("#### Medicines that fail first")
            first = aff.nsmallest(10, "surge_days")[
                ["facility_name", "district", "sku_name", "current_stock",
                 "daily_burn", "surge_burn", "days_to_stockout",
                 "surge_days", "days_lost"]].round(1)
            first.columns = ["Facility", "District", "Medicine", "Stock",
                             "Normal burn", "Surge burn", "Normal days",
                             "Surge days", "Days lost"]
            st.dataframe(first, use_container_width=True, hide_index=True)

            st.error(T(
                f"**Under {spick.lower()}, {int(s.fail_before_onset)} "
                f"facility-medicine pairs deplete inside the "
                f"{int(s.onset_days)}-day onset window** — faster than a "
                f"district indent can be raised and delivered "
                f"({LEAD_TIME_NOTE}). Pre-positioning has to happen before the "
                f"surge is visible in case counts, which is what the forecast "
                f"and redistribution layers exist to enable.", LANG))

# ---------------------------------------------------------------- preventable
with tab4:
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
        ipick = st.selectbox(
            "Inspect facility-SKU",
            show.apply(lambda r: f"{r.facility_name} — {r.sku_name}", axis=1))
        fn, sn = ipick.split(" — ")
        row = show[(show.facility_name == fn) & (show.sku_name == sn)].iloc[0]

        hist = ledger[(ledger.facility_id == row.facility_id) &
                      (ledger.sku_code == row.sku_code)].tail(120)

        f = go.Figure()
        f.add_scatter(x=hist.date, y=hist.closing_stock, name="Stock on hand",
                      line=dict(color="#5B8DEF", width=2))
        f.add_hline(y=row.reorder_point, line_dash="dash",
                    line_color="#FBBF24", annotation_text="Reorder point")
        f.add_hline(y=0, line_color="#F43F5E")
        f.update_layout(height=300, yaxis_title="Units")
        st.plotly_chart(style.dark(f), use_container_width=True)

        st.info(T(
            f"**{row.facility_name}** has **{int(row.current_stock)} units** "
            f"of {row.sku_name}, burning **{row.daily_burn}/day** — depletion "
            f"in **{row.days_to_stockout} days**, against a reorder point of "
            f"**{int(row.reorder_point)} units**.", LANG))

# ---------------------------------------------------------------- transfers
with tab5:
    st.subheader("Recommended transfers — surplus to shortage")
    st.caption(f"{len(transfers)} orders · "
               f"{int(transfers.cross_district.sum())} cross-district · "
               f"{int(transfers.quantity.sum()):,} units · "
               f"mean {transfers.road_km.mean():.0f} km")

    st.info(T(
        "**These are recommendations, not instructions.** The optimiser "
        "proposes; a district officer approves, modifies or rejects. Nothing "
        "moves without human authorisation — stock transfers carry clinical "
        "and audit consequences that a solver cannot weigh.", LANG))

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

            if LANG:
                a.caption(T(
                    f"Move {r.quantity} units of {r.sku_name} from "
                    f"{r.from_facility} to {r.to_facility}. Distance "
                    f"{r.road_km} km. This covers {int(r.courses_covered)} "
                    f"treatment courses.", LANG))

            key = f"{r.from_facility}_{r.to_facility}_{r.sku_code}"
            state = st.session_state.get(f"st_{key}")
            ac1, ac2, ac3 = a.columns(3)

            if state:
                a.success(f"**{state}** — logged for district approval")
            else:
                for col, label, result in [
                        (ac1, "Approve", "Approved"),
                        (ac2, "Modify", "Sent back for revision"),
                        (ac3, "Reject", "Rejected")]:
                    if col.button(label, key=f"{label}_{key}",
                                  use_container_width=True):
                        st.session_state[f"st_{key}"] = result
                        st.rerun()

# ---------------------------------------------------------------- AI briefs
with tab6:
    st.subheader("Gemini-generated field briefings")
    st.caption("Each alert is converted into an operational briefing an officer "
               "can act on, and translated for the PHC pharmacist. Gemini "
               "receives stock level, burn rate, reorder point, season and "
               "transfer options — and turns them into an instruction. "
               "Generated ahead of time and cached, so the demo never depends "
               "on a live API call.")

    if not briefs:
        st.warning("No briefs cached. Run `python src/gemini/briefs.py`.")
    else:
        items = sorted(briefs.items(), key=lambda kv: kv[1]["days_to_stockout"])
        labels = [f"{v['facility']} — {v['sku']} ({v['days_to_stockout']:.0f}d)"
                  for _, v in items]
        idx = st.selectbox("Select alert", range(len(labels)),
                           format_func=lambda i: labels[i])
        b = items[idx][1]

        ac, cc = st.columns(2)
        with ac:
            st.markdown("**English — district health officer**")
            st.info(b["english"])
        with cc:
            st.markdown("**తెలుగు — PHC pharmacist**")
            style.telugu(st, b["telugu"] or "—")

        st.caption(f"{len(briefs)} briefings cached across "
                   f"{len({v['facility'] for v in briefs.values()})} facilities")

# ---------------------------------------------------------------- federation
with tab7:
    st.subheader("Federated learning across nodes")
    st.caption("Each node trains on its own data. Only model coefficients and "
               "feature statistics are exchanged — no inventory records, no "
               "patient data, no facility rows cross a node boundary.")

    st.info(
        "**How these nodes are constructed.** The three nodes are simulated by "
        "partitioning our districts and giving each a deliberately different "
        "amount of training history — 18, 9 and 3 months. They carry state "
        "names to make the scenario legible, but the underlying facilities are "
        "all in Telangana. What is demonstrated is the *federation mechanism*, "
        "which is identical regardless of how nodes are partitioned: each node "
        "trains locally, shares only weights, and receives a blended model "
        "weighted by its own data volume.")

    if not fed:
        st.warning("No federation results. Run `python src/federated/fedavg.py`.")
    else:
        fdf = pd.DataFrame(fed)

        f = go.Figure()
        f.add_bar(x=fdf.node, y=fdf.local_mape, name="Trained alone",
                  marker_color="#F43F5E")
        f.add_bar(x=fdf.node, y=fdf.federated_mape, name="With federation",
                  marker_color="#34D399")
        f.update_layout(barmode="group", height=380,
                        yaxis_title="Forecast error (MAPE %)")
        st.plotly_chart(style.dark(f), use_container_width=True)

        st.dataframe(fdf, use_container_width=True, hide_index=True)

        best = fdf.loc[fdf["improvement_%"].idxmax()]
        st.success(T(
            f"**{best['node']}** has only {int(best['train_rows']):,} training "
            f"rows — too little to learn monsoon seasonality alone. Federation "
            f"reduces its forecast error from {best['local_mape']}% to "
            f"{best['federated_mape']}% ({best['improvement_%']}% better), "
            f"without a single data row leaving the node.", LANG))

        st.markdown("""
**What crosses a node boundary:** model coefficients and feature statistics only.
**What never leaves:** inventory records, patient counts, facility data.

The gain scales inversely with local data volume: data-rich nodes are
essentially unaffected, while data-poor nodes gain substantially. The blend
weight is set by each node's own data volume, so a node with abundant history
keeps its local model almost entirely — which is why the data-rich result sits
close to zero rather than improving. Seasonality is shared structure, so it can
be learned collectively without pooling the underlying data.
""")

# ---------------------------------------------------------------- resilience
with tab8:
    st.subheader("Operational PHC Resilience Index")
    st.caption("A prototype policy index, not a validated instrument. It "
               "combines medicine availability (40%), stock-out urgency (20%), "
               "staff availability (20%) and bed headroom (20%) into one ranked "
               "figure, so a district officer can see where to intervene first "
               "rather than reading four separate tables. The weights are a "
               "starting proposal and would need calibration against outcome "
               "data before operational use.")

    b1, b2, b3, b4 = st.columns(4)
    for col, name in zip([b1, b2, b3, b4],
                         ["HIGH RISK", "AT RISK", "STABLE", "RESILIENT"]):
        col.metric(name.title(), int((resil.band == name).sum()))

    st.divider()

    w = resil.iloc[0]
    st.markdown(f"### Most vulnerable: {w.facility_name}")

    s1, s2 = st.columns([1, 2])
    with s1:
        style.score_card(st, int(w.score), w.band)

    with s2:
        factors = pd.DataFrame({
            "Factor": ["Medicine availability", "Stock-out urgency",
                       "Staff availability", "Bed headroom"],
            "Score": [w.supply_pct, w.urgency_pct,
                      w.staffing_pct, w.capacity_pct],
        })
        fg = go.Figure()
        fg.add_bar(x=factors.Score, y=factors.Factor, orientation="h",
                   marker_color=["#F43F5E" if v < 50 else
                                 "#FBBF24" if v < 75 else "#34D399"
                                 for v in factors.Score],
                   text=[f"{v:.0f}%" for v in factors.Score],
                   textposition="outside")
        fg.update_layout(height=215, xaxis_range=[0, 118], showlegend=False)
        st.plotly_chart(style.dark(fg), use_container_width=True)

    st.error(T(
        f"**Primary risk:** {w.primary_risk} — "
        f"{'already at zero' if w.days_to_next_stockout == 0 else f'{w.days_to_next_stockout:.1f} days to stock-out'}  \n"
        f"**Weakest factor:** {w.weakest_factor}  \n"
        f"**Supply status:** {int(w.skus_stocked_out)} of {int(w.skus_total)} "
        f"medicines already at zero, {int(w.skus_critical)} more running out",
        LANG))

    st.divider()
    st.markdown("#### All facilities, ranked by vulnerability")

    rf = go.Figure()
    for bnd in ["HIGH RISK", "AT RISK", "STABLE", "RESILIENT"]:
        sub = resil[resil.band == bnd]
        if len(sub):
            rf.add_bar(x=sub.score, y=sub.facility_name, orientation="h",
                       name=bnd, marker_color=BAND_COLOR[bnd],
                       hovertemplate="<b>%{y}</b><br>index %{x}<extra></extra>")
    rf.update_layout(height=760, barmode="stack",
                     xaxis_title="Resilience index (0–100)",
                     yaxis=dict(autorange="reversed"))
    st.plotly_chart(style.dark(rf), use_container_width=True)

    with st.expander("Index breakdown, all facilities"):
        st.dataframe(
            resil[["facility_name", "facility_type", "district", "score",
                   "band", "supply_pct", "urgency_pct", "staffing_pct",
                   "capacity_pct", "skus_stocked_out", "primary_risk"]],
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
        "**Data note.** Bed occupancy and staff attendance are generated "
        "against Indian Public Health Standards norms — 6 beds and 2 doctors "
        "per PHC, 30 beds and 6 doctors per CHC — with vacancy correlated to "
        "each facility's supply stress. No public API exposes either live. The "
        "index computes identically on real HMIS attendance data.")

# ---------------------------------------------------------------- evidence
with tab9:
    st.subheader("How this data was constructed")
    st.caption("Live PHC inventory APIs are not publicly available in India. "
               "Rather than generating random numbers, consumption is computed "
               "from district disease incidence through published clinical "
               "treatment courses. Here is exactly how, and what that does and "
               "does not prove.")
    if LANG:
        st.info("This methodology section is maintained in English. It "
                "documents data provenance and model design for reviewers and "
                "programme staff; the operational views — alerts, briefings, "
                "recommendations and transfer orders — are delivered in "
                f"{lang_label}.")

    d = st.selectbox("District", sorted(disease.district.unique()))

    ors = ledger[(ledger.district == d) &
                 (ledger.sku_code == "ORS001")].copy()
    ors["month"] = ors.date.dt.to_period("M").astype(str)
    om = ors.groupby("month").issues.sum()

    dia = disease[(disease.district == d) &
                  (disease.disease == "diarrhoeal")].copy()
    dia["month"] = dia.week_start.dt.to_period("M").astype(str)
    dm = dia.groupby("month").case_count.sum()

    comp = pd.DataFrame({"Diarrhoeal cases": dm, "ORS issued": om}).dropna()

    f = go.Figure()
    f.add_scatter(x=comp.index, y=comp["Diarrhoeal cases"],
                  name="Diarrhoeal cases", line=dict(color="#F43F5E", width=2))
    f.add_scatter(x=comp.index, y=comp["ORS issued"], name="ORS issued",
                  yaxis="y2", line=dict(color="#5B8DEF", width=2))
    f.update_layout(height=340, yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(style.dark(f), use_container_width=True)

    rval = comp.iloc[:, 0].corr(comp.iloc[:, 1])
    m1, m2 = st.columns([1, 3])
    m1.metric("Correlation", f"{rval:.3f}")
    m2.warning(
        "**This correlation is expected, not discovered.** ORS consumption was "
        "*derived* from diarrhoeal case counts at 6 sachets per case, so the "
        "two series are related by construction. The chart confirms the "
        "generator applies clinical norms consistently across 18 months and "
        "three districts — it is a validation of the construction, not evidence "
        "that the data matches real PHC records.")

    st.markdown("""
#### What is real

- **Facility locations** — real Telangana mandal headquarters. Indian PHCs are
  sited at mandal HQ under IPHS. Six are confirmed PHC sites in NHM's published
  Hospital Development Society list.
- **District structure** — Nalgonda, Yadadri Bhuvanagiri and Suryapet are real
  districts. Facility counts follow IPHS: 1 PHC per ~30,000 rural population,
  1 CHC per ~120,000.
- **Medicine list** — drawn from the National List of Essential Medicines.
- **Diarrhoeal incidence and treatment rates** — calibrated against NFHS-5
  (2019–21) measured values for Telangana: 5.46% two-week prevalence in
  under-5s, 61.8% receiving ORS, 39.3% receiving zinc, and 71.1% of cases
  reaching a health provider.
- **Seasonal shape** — calibrated against 218 IDSP outbreak reports for
  Telangana (2009–2023) via the EpiClim dataset. Diarrhoeal outbreaks cluster
  in July, August, June and September; vector-borne in August, July, September.
- **Clinical consumption norms** — ORS at 6 sachets per diarrhoeal case,
  artemether-lumefantrine at 1 course per malaria case, from standard
  treatment guidelines.

#### What is synthesised

- **Stock levels, receipts and issues.** No public API exposes live PHC
  inventory. These are computed forward from disease incidence through the
  clinical norms above, with procurement modelled as a 30-day indent cycle,
  7–21 day lead times, and probabilistic delivery delays that differ by
  district.
- **Patient footfall**, derived from incidence, catchment and IPHS
  service-load norms.
- **Bed occupancy and staff attendance**, generated against IPHS norms.

#### On the seasonality calibration

IDSP records outbreak *reports*, not routine caseload. A low-report month means
fewer outbreaks were declared, not that incidence collapsed. We use the IDSP
monthly distribution as the **shape** of the curve, compressed around 1.0 to
keep amplitude plausible for routine demand. The peak ordering is preserved
exactly; the amplitude is not taken literally.

#### Point-in-time correctness

IDSP surveillance is published weekly, in arrears. A forecast made on a Tuesday
cannot use that week's completed case count. All disease features are therefore
lagged by at least one full week, and the weekly series is shifted before
joining to daily records — so no same-week value can leak into the feature
matrix. This costs accuracy, and that is the point: the reported figures are
what the system would achieve in production.

#### What this does not claim

This data is **structurally plausible, not empirically validated**. It
reproduces the shape of the problem — monsoon demand spikes, indent-cycle
sawtooth patterns, chronic under-supply in specific districts — but the
specific numbers are not measurements of any real facility.

#### Why that is sufficient for this prototype

The system's value is in the pipeline, not the numbers: forecasting from
surveillance, converting forecasts to reorder decisions, solving redistribution
under constraints, and federating models without pooling data. Every one of
those operates identically on real DVDMS records.

The ingestion schema (`docs/openapi.yaml`) specifies how DVDMS-shaped records
enter the system. A state connects its live export at that interface and the
synthetic layer is replaced — nothing downstream changes. The endpoints are
specified but not yet implemented.
""")