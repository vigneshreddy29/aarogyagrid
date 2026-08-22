"""
AarogyaGrid — demand forecasting.

Ridge regression per SKU. Chosen deliberately:
  - trains in seconds, cannot fail to converge
  - coefficients average cleanly -> federated learning is trivial
  - fully interpretable, which matters to a health ministry judge
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
    """Feature matrix per facility-SKU-day."""
    df = ledger.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["facility_id", "sku_code", "date"]).reset_index(drop=True)

    key = ["facility_id", "sku_code"]
    g = df.groupby(key)["issues"]

    df["lag_1"]  = g.shift(1)
    df["lag_7"]  = g.shift(7)
    df["lag_14"] = g.shift(14)

    # transform() keeps alignment without index gymnastics
    df["roll_7"]  = df.groupby(key)["issues"].transform(
        lambda s: s.shift(1).rolling(7).mean())
    df["roll_28"] = df.groupby(key)["issues"].transform(
        lambda s: s.shift(1).rolling(28).mean())
    df["std_7"]   = df.groupby(key)["issues"].transform(
        lambda s: s.shift(1).rolling(7).std())

    # ---- the differentiator: real disease surveillance as a feature ----
    dis = disease.copy()
    dis["week_start"] = pd.to_datetime(dis["week_start"])

    sku_disease = {c: d for c, _, _, d, _, _ in SKUS}
    df["sku_disease"] = df["sku_code"].map(sku_disease)
    df["week_start"] = df["date"].dt.to_period("W-MON").dt.start_time

    dis = dis.rename(columns={"disease": "sku_disease",
                              "case_count": "disease_cases"})
    df = df.merge(dis[["district", "week_start", "sku_disease", "disease_cases"]],
                  on=["district", "week_start", "sku_disease"], how="left")
    df["disease_cases"] = df["disease_cases"].fillna(0)

    df = df.sort_values(key + ["date"]).reset_index(drop=True)
    df["disease_lag_7"] = df.groupby(key)["disease_cases"].shift(7)
    df["disease_ma_28"] = df.groupby(key)["disease_cases"].transform(
        lambda s: s.shift(1).rolling(28).mean())
    df["disease_trend"] = df["disease_cases"] / (df["disease_ma_28"] + 1)

    # seasonality
    doy = df["date"].dt.dayofyear
    df["sin_year"] = np.sin(2 * np.pi * doy / 365.25)
    df["cos_year"] = np.cos(2 * np.pi * doy / 365.25)
    df["dow"] = df["date"].dt.dayofweek

    return df


FEATURES = ["lag_1", "lag_7", "lag_14", "roll_7", "roll_28", "std_7",
            "disease_cases", "disease_lag_7", "disease_trend",
            "sin_year", "cos_year", "dow"]


def mape(y, yhat):
    m = y > 0
    return float(np.mean(np.abs(y[m] - yhat[m]) / y[m]) * 100)


def main():
    ledger  = pd.read_parquet(f"{OUT}/stock_ledger.parquet")
    disease = pd.read_parquet(f"{OUT}/disease_weekly.parquet")

    print("building features ...")
    df = build_features(ledger, disease).dropna(subset=FEATURES + ["issues"])

    split = df["date"].max() - pd.Timedelta(days=90)
    train, test = df[df.date <= split], df[df.date > split]
    print(f"train {len(train):,}   test {len(test):,}\n")

    models, results = {}, []
    for code, name, *_ in SKUS:
        tr = train[train.sku_code == code]
        te = test[test.sku_code == code]
        if len(tr) < 100:
            continue

        scaler = StandardScaler().fit(tr[FEATURES])
        model = Ridge(alpha=1.0).fit(scaler.transform(tr[FEATURES]), tr["issues"])

        pred     = np.maximum(0, model.predict(scaler.transform(te[FEATURES])))
        baseline = te["roll_7"].values          # seasonal-naive comparison

        m_model = mape(te["issues"].values, pred)
        m_base  = mape(te["issues"].values, baseline)

        models[code] = {"model": model, "scaler": scaler,
                        "resid_std": float(np.std(te["issues"].values - pred))}
        results.append({"sku": name, "ridge_mape": round(m_model, 2),
                        "baseline_mape": round(m_base, 2),
                        "improvement_%": round((m_base - m_model) / m_base * 100, 1)})

    print(pd.DataFrame(results).to_string(index=False))

    with open(f"{MODELS}/forecast_models.pkl", "wb") as f:
        pickle.dump(models, f)

    df.to_parquet(f"{OUT}/features.parquet", index=False)
    print(f"\nsaved {len(models)} models -> {MODELS}/forecast_models.pkl")


if __name__ == "__main__":
    main()