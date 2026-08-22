"""
AarogyaGrid — demand forecasting.

Ridge regression per SKU. Chosen deliberately:
  - trains in seconds, cannot fail to converge
  - coefficients average cleanly -> federated learning is trivial
  - fully interpretable, which matters to a health ministry judge

POINT-IN-TIME CORRECTNESS
-------------------------
IDSP disease surveillance is published weekly, in arrears. A forecast made
on Tuesday cannot use that week's completed case count — it does not exist
yet. All disease features are therefore lagged by at least one full week
(t-1, t-2, and a 4-week trailing mean). No same-week disease value enters
the feature matrix.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import pickle

from src.config import SKUS

OUT = "data/processed"
MODELS = "models"
os.makedirs(MODELS, exist_ok=True)


def build_features(ledger, disease):
    """Feature matrix per facility-SKU-day, point-in-time correct."""
    df = ledger.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["facility_id", "sku_code", "date"]).reset_index(drop=True)

    key = ["facility_id", "sku_code"]
    g = df.groupby(key)["issues"]

    # ---- consumption history (all strictly lagged) ----------------------
    df["lag_1"]  = g.shift(1)
    df["lag_7"]  = g.shift(7)
    df["lag_14"] = g.shift(14)

    df["roll_7"]  = df.groupby(key)["issues"].transform(
        lambda s: s.shift(1).rolling(7).mean())
    df["roll_28"] = df.groupby(key)["issues"].transform(
        lambda s: s.shift(1).rolling(28).mean())
    df["std_7"]   = df.groupby(key)["issues"].transform(
        lambda s: s.shift(1).rolling(7).std())

    # seasonal-naive reference: same weekday, 7 days ago
    df["seasonal_naive"] = g.shift(7)

    # ---- disease surveillance, LAGGED ----------------------------------
    dis = disease.copy()
    dis["week_start"] = pd.to_datetime(dis["week_start"])
    dis = dis.rename(columns={"disease": "sku_disease",
                              "case_count": "disease_cases"})
    dis = dis.sort_values(["district", "sku_disease", "week_start"])

    # Shift the weekly series BEFORE joining: week t-1 is the most recent
    # report available when forecasting inside week t.
    dgrp = dis.groupby(["district", "sku_disease"])["disease_cases"]
    dis["dis_w1"] = dgrp.shift(1)          # previous reported week
    dis["dis_w2"] = dgrp.shift(2)          # two weeks back
    dis["dis_ma4"] = dgrp.transform(
        lambda s: s.shift(1).rolling(4).mean())

    sku_disease = {c: d for c, _, _, d, _, _ in SKUS}
    df["sku_disease"] = df["sku_code"].map(sku_disease)
    df["week_start"] = df["date"].dt.to_period("W-MON").dt.start_time

    df = df.merge(
        dis[["district", "week_start", "sku_disease",
             "dis_w1", "dis_w2", "dis_ma4"]],
        on=["district", "week_start", "sku_disease"], how="left")

    for c in ["dis_w1", "dis_w2", "dis_ma4"]:
        df[c] = df[c].fillna(0.0)

    # direction of travel in the surveillance signal, using lagged values only
    df["dis_trend"] = (df["dis_w1"] / (df["dis_ma4"] + 1)).clip(0.3, 4.0)

    # ---- calendar seasonality ------------------------------------------
    doy = df["date"].dt.dayofyear
    df["sin_year"] = np.sin(2 * np.pi * doy / 365.25)
    df["cos_year"] = np.cos(2 * np.pi * doy / 365.25)
    df["dow"] = df["date"].dt.dayofweek

    return df


FEATURES = ["lag_1", "lag_7", "lag_14", "roll_7", "roll_28", "std_7",
            "dis_w1", "dis_w2", "dis_ma4", "dis_trend",
            "sin_year", "cos_year", "dow"]


# ---------------------------------------------------------------- metrics

def mape(y, yhat):
    m = y > 0
    return float(np.mean(np.abs(y[m] - yhat[m]) / y[m]) * 100)


def wape(y, yhat):
    """Weighted absolute percentage error — robust to near-zero actuals."""
    d = np.sum(np.abs(y))
    return float(np.sum(np.abs(y - yhat)) / d * 100) if d else np.nan


def mae(y, yhat):
    return float(np.mean(np.abs(y - yhat)))


def rmse(y, yhat):
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def score(y, yhat):
    return {"MAE": round(mae(y, yhat), 2), "RMSE": round(rmse(y, yhat), 2),
            "WAPE": round(wape(y, yhat), 2), "MAPE": round(mape(y, yhat), 2)}


# ---------------------------------------------------------------- main

def main():
    ledger  = pd.read_parquet(f"{OUT}/stock_ledger.parquet")
    disease = pd.read_parquet(f"{OUT}/disease_weekly.parquet")

    print("building features (point-in-time correct) ...")
    df = build_features(ledger, disease).dropna(
        subset=FEATURES + ["issues", "seasonal_naive"])

    split = df["date"].max() - pd.Timedelta(days=90)
    train, test = df[df.date <= split], df[df.date > split]
    print(f"train {len(train):,}   test {len(test):,}\n")

    models, rows, detail = {}, [], []

    for code, name, *_ in SKUS:
        tr = train[train.sku_code == code]
        te = test[test.sku_code == code]
        if len(tr) < 100 or len(te) < 20:
            continue

        scaler = StandardScaler().fit(tr[FEATURES])
        model = Ridge(alpha=1.0).fit(scaler.transform(tr[FEATURES]), tr["issues"])

        y = te["issues"].values
        preds = {
            "Naive (yesterday)":     te["lag_1"].values,
            "7-day moving average":  te["roll_7"].values,
            "Seasonal naive (t-7)":  te["seasonal_naive"].values,
            "Ridge + surveillance":  np.maximum(0, model.predict(scaler.transform(te[FEATURES]))),
        }

        # Per-SKU model selection: Ridge only where it actually beats the
        # naive baseline on held-out data. For sparse, event-driven SKUs
        # (cholera antibiotics) the surveillance signal is mostly noise and
        # naive persistence wins — so we use it.
        ridge_mape = mape(y, preds["Ridge + surveillance"])
        naive_mape = mape(y, preds["Naive (yesterday)"])
        use_ridge = ridge_mape < naive_mape

        models[code] = {"model": model, "scaler": scaler,
                        "use_ridge": use_ridge,
                        "fallback": "naive" if not use_ridge else None,
                        "resid_std": float(np.std(
                            y - (preds["Ridge + surveillance"] if use_ridge
                                 else preds["Naive (yesterday)"])))}

        for label, p in preds.items():
            detail.append({"sku": name, "model": label, **score(y, p)})

        best_base = min(mape(y, preds["Naive (yesterday)"]),
                        mape(y, preds["7-day moving average"]),
                        mape(y, preds["Seasonal naive (t-7)"]))
        ridge_m = mape(y, preds["Ridge + surveillance"])

        rows.append({"sku": name,
                     "ridge_mape": round(ridge_m, 2),
                     "best_baseline_mape": round(best_base, 2),
                     "improvement_%": round((best_base - ridge_m) / best_base * 100, 1),
                     "model_used": "Ridge" if use_ridge else "Naive (fallback)",
                     "ridge_wape": round(wape(y, preds["Ridge + surveillance"]), 2)})

    summary = pd.DataFrame(rows)
    print("--- Ridge vs best of three baselines ---")
    print(summary.to_string(index=False))

    full = pd.DataFrame(detail)
    full.to_csv(f"{OUT}/forecast_metrics.csv", index=False)
    print(f"\n--- all baselines, all metrics (saved to forecast_metrics.csv) ---")
    print(full.pivot_table(index="sku", columns="model", values="MAPE").round(2).to_string())

    with open(f"{MODELS}/forecast_models.pkl", "wb") as f:
        pickle.dump(models, f)

    df.to_parquet(f"{OUT}/features.parquet", index=False)
    print(f"\nsaved {len(models)} models -> {MODELS}/forecast_models.pkl")


if __name__ == "__main__":
    main()