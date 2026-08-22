"""
Patient footfall — the missing link in the demand chain.

    PATIENT FOOTFALL  →  DEMAND SIGNAL  →  MEDICINE NEED

The problem statement asks for visibility into "medicines, patient footfall,
and resource utilisation". Footfall is the operational signal that sits
between disease in the community and stock moving off a PHC shelf: a case
only consumes medicine once the patient walks in.

Derived from:
  - district disease incidence (weekly, from the surveillance series)
  - facility catchment population
  - NFHS-5 Telangana: 71.09% of cases reach a health provider
  - IPHS service-load norms for PHC and CHC

Outputs daily OPD, IPD, emergency and referral counts per facility, plus
the 7-day trend that drives the demand relationship shown in the console.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd
from datetime import timedelta

from src.config import RANDOM_SEED, NFHS_FACILITY_SEEKING

rng = np.random.default_rng(RANDOM_SEED + 11)
OUT = "data/processed"

# Share of catchment presenting daily for non-outbreak reasons (chronic care,
# maternal health, immunisation, minor injury) — IPHS service-load norms.
BASELINE_OPD_RATE = {"PHC": 0.0032, "CHC": 0.0021}

IPD_SHARE       = {"PHC": 0.018, "CHC": 0.062}   # of OPD, admitted
EMERGENCY_SHARE = {"PHC": 0.021, "CHC": 0.048}   # of OPD, emergency
REFERRAL_SHARE  = {"PHC": 0.055, "CHC": 0.019}   # of OPD, referred upward

# minutes of clinician time per OPD visit — drives waiting-time estimate
MINUTES_PER_VISIT = 6.5


def main():
    fac = pd.read_parquet(f"{OUT}/facilities.parquet")
    dis = pd.read_parquet(f"{OUT}/disease_weekly.parquet")
    led = pd.read_parquet(f"{OUT}/stock_ledger.parquet")
    status = pd.read_parquet(f"{OUT}/facility_status.parquet")

    dis["week_start"] = pd.to_datetime(dis["week_start"])
    led["date"] = pd.to_datetime(led["date"])

    dates = pd.Series(sorted(led["date"].unique()))
    weeks = sorted(dis["week_start"].unique())

    # district-week total caseload across all tracked diseases
    dw = (dis.groupby(["district", "week_start"])["case_count"].sum()
             .to_dict())
    dist_pop = fac.groupby("district")["catchment_population"].sum().to_dict()

    staff = status.set_index("facility_id")["staff_present_pct"].to_dict()

    rows = []
    for f in fac.itertuples():
        share = f.catchment_population / dist_pop[f.district]
        base_rate = BASELINE_OPD_RATE[f.facility_type]
        s_pct = staff.get(f.facility_id, 85.0)

        for d in dates:
            d = pd.Timestamp(d)
            wk = max([w for w in weeks if w <= d], default=weeks[0])
            district_cases = dw.get((f.district, wk), 0)

            # outbreak-driven arrivals: cases attributable to this facility's
            # catchment, of which NFHS says ~71% actually seek care
            outbreak = (district_cases * share / 7.0) * NFHS_FACILITY_SEEKING

            # steady-state arrivals unrelated to the tracked diseases
            baseline = f.catchment_population * base_rate

            # weekday effect — Monday is heaviest at Indian PHCs
            dow_mult = [1.28, 1.06, 1.00, 0.98, 1.02, 0.88, 0.42][d.dayofweek]

            opd = max(0, (baseline + outbreak) * dow_mult * rng.uniform(0.9, 1.1))

            ipd = opd * IPD_SHARE[f.facility_type] * rng.uniform(0.8, 1.2)
            emg = opd * EMERGENCY_SHARE[f.facility_type] * rng.uniform(0.7, 1.3)
            ref = opd * REFERRAL_SHARE[f.facility_type] * rng.uniform(0.8, 1.2)

            # waiting time rises when fewer clinicians are present
            clinicians = max(1.0, (s_pct / 100) * (2 if f.facility_type == "PHC" else 6))
            # OPD runs ~4 hours; queue time = arrivals beyond service capacity
            capacity = clinicians * (240 / MINUTES_PER_VISIT)
            wait_min = float(np.clip(12 + (opd / max(capacity, 1)) * 34, 8, 95))

            rows.append({
                "facility_id": f.facility_id,
                "facility_name": f.facility_name,
                "facility_type": f.facility_type,
                "district": f.district,
                "date": d,
                "opd_visits": int(round(opd)),
                "ipd_admissions": int(round(ipd)),
                "emergency_cases": int(round(emg)),
                "referrals": int(round(ref)),
                "avg_wait_min": round(wait_min, 1),
                "outbreak_share": round(outbreak / max(opd, 1e-6), 3),
            })

    df = pd.DataFrame(rows).sort_values(["facility_id", "date"])

    # 7-day trend: current week vs the week before
    g = df.groupby("facility_id")["opd_visits"]
    df["opd_7d"]   = g.transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["opd_prev7"] = g.transform(
        lambda s: s.shift(7).rolling(7, min_periods=1).mean())
    df["opd_trend_pct"] = ((df["opd_7d"] / df["opd_prev7"] - 1) * 100).round(1)

    df.to_parquet(f"{OUT}/footfall.parquet", index=False)

       # ---- the demand relationship ---------------------------------------
    # Measured weekly (daily noise in both series is independent) and only on
    # days when stock was actually available — a stocked-out facility issues
    # nothing no matter how many patients arrive, which would mask the link.
    latest = df["date"].max()
    win = df[df.date > latest - timedelta(days=180)]

    stocked = led[(led.date > latest - timedelta(days=180)) &
                  (led.closing_stock > 0)]
    daily_iss = (stocked.groupby(["facility_id", "date"])["issues"].sum()
                        .reset_index().rename(columns={"issues": "units"}))

    joined = win[["facility_id", "date", "opd_visits"]].merge(
        daily_iss, on=["facility_id", "date"], how="inner")
    joined["week"] = joined["date"].dt.to_period("W-MON").dt.start_time

    weekly = (joined.groupby(["facility_id", "week"])
                    .agg(opd=("opd_visits", "sum"), units=("units", "sum"))
                    .reset_index())

    link = (weekly.groupby("facility_id")
                  .apply(lambda g: g["opd"].corr(g["units"]) if len(g) > 4 else np.nan,
                         include_groups=False)
                  .rename("footfall_demand_r").reset_index().dropna())
    link.to_parquet(f"{OUT}/footfall_link.parquet", index=False)
    weekly.to_parquet(f"{OUT}/footfall_weekly.parquet", index=False)

    today = df[df.date == latest]
    print(f"{len(df):,} facility-days across {df.facility_id.nunique()} facilities")
    print(f"\n--- today ({latest.date()}) ---")
    print(f"OPD visits       {today.opd_visits.sum():,}")
    print(f"IPD admissions   {today.ipd_admissions.sum():,}")
    print(f"Emergency cases  {today.emergency_cases.sum():,}")
    print(f"Referrals        {today.referrals.sum():,}")
    print(f"Mean wait        {today.avg_wait_min.mean():.0f} min")

    print(f"\n--- 7-day footfall trend, busiest 5 ---")
    print(today.nlargest(5, "opd_trend_pct")[
        ["facility_name", "opd_visits", "opd_7d", "opd_trend_pct"]]
        .round(1).to_string(index=False))

    print(f"\n--- footfall → medicine demand correlation ---")
    print(f"median r across facilities: {link.footfall_demand_r.median():.3f}")
    print(f"facilities with r > 0.5:    {(link.footfall_demand_r > 0.5).sum()} "
          f"of {len(link)}")

    print(f"\nsaved -> {OUT}/footfall.parquet, {OUT}/footfall_link.parquet")


if __name__ == "__main__":
    main()