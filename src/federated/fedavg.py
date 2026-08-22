"""
AarogyaGrid — federated learning across state nodes.

Each state trains locally. Only Ridge COEFFICIENTS and feature summary
statistics are shared — never inventory records, never patient data.

This is why Ridge was chosen over a neural forecaster: linear model
weights average cleanly, and the privacy claim is easy to verify by
inspection.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from src.forecast.train import FEATURES, mape

OUT = "data/processed"

# Simulated state nodes. Data volume differs deliberately: the whole point
# of federation is that a data-poor state benefits from shared structure.
NODES = {
    "Telangana (data-rich)":  {"district": "Nalgonda",            "months": 18},
    "Odisha (moderate)":      {"district": "Suryapet",            "months": 9},
    "Meghalaya (data-poor)":  {"district": "Yadadri Bhuvanagiri", "months": 3},
}

SKU = "ORS001"
BLEND_K = 2000          # controls how much a node leans on the federation


def local_train(df, months):
    """Train on the most recent N months only — simulates a state's own history."""
    cutoff = df.date.max() - pd.Timedelta(days=months * 30)
    tr = df[(df.date >= cutoff) & (df.date <= df.date.max() - pd.Timedelta(days=60))]
    te = df[df.date > df.date.max() - pd.Timedelta(days=60)]
    if len(tr) < 60 or len(te) < 20:
        return None

    sc = StandardScaler().fit(tr[FEATURES])
    sc.scale_ = np.where(sc.scale_ > 1e-8, sc.scale_, 1.0)
    m = Ridge(alpha=1.0).fit(sc.transform(tr[FEATURES]), tr["issues"])
    pred = np.maximum(0, m.predict(sc.transform(te[FEATURES])))
    return {"model": m, "scaler": sc, "n": len(tr), "train": tr,
            "mape": mape(te["issues"].values, pred), "test": te}


def main():
    feats = pd.read_parquet(f"{OUT}/features.parquet")
    feats = feats[feats.sku_code == SKU].dropna(subset=FEATURES + ["issues"])

    # ---- 1. local training, in isolation --------------------------------
    print("--- local training (no data shared) ---")
    local = {}
    for name, cfg in NODES.items():
        sub = feats[feats.district == cfg["district"]]
        r = local_train(sub, cfg["months"])
        if not r:
            print(f"{name:26s} SKIPPED — only {len(sub)} rows")
            continue
        local[name] = r
        print(f"{name:26s} n={r['n']:6,}  local MAPE {r['mape']:.2f}%")

    if len(local) < 2:
        print("\nNeed at least 2 nodes. Check district names in NODES.")
        return

    # ---- 2. federated feature normalisation ------------------------------
    # Nodes share only summary statistics (means, variances, counts) so every
    # node standardises features identically. No raw rows move.
    total = sum(r["n"] for r in local.values())
    g_mean = sum(r["scaler"].mean_ * (r["n"] / total) for r in local.values())
    g_var  = sum(r["scaler"].var_  * (r["n"] / total) for r in local.values())

    g_scaler = StandardScaler()
    g_scaler.mean_ = g_mean
    g_scaler.var_ = g_var
    # a feature with zero variance at a node would divide to NaN
    g_scaler.scale_ = np.sqrt(np.where(g_var > 1e-8, g_var, 1.0))
    g_scaler.n_features_in_ = len(FEATURES)

    # ---- 3. retrain locally on the shared scale, then average -------------
    coefs, intercepts = [], []
    for name, r in local.items():
        tr = r["train"]
        m = Ridge(alpha=1.0).fit(g_scaler.transform(tr[FEATURES]), tr["issues"])
        r["aligned"] = m
        coefs.append(m.coef_ * (r["n"] / total))
        intercepts.append(m.intercept_ * (r["n"] / total))

    coef = sum(coefs)
    intercept = sum(intercepts)

    print(f"\n--- federated aggregation ---")
    print(f"FedAvg over {len(local)} nodes — {len(coef)} coefficients "
          f"+ {len(g_mean)} feature statistics shared")
    print("NO inventory rows, patient records, or facility data transmitted.")

    # ---- 4. personalised blending ----------------------------------------
    # Data-rich nodes keep their own signal; data-poor nodes lean on the
    # global model. Standard personalised federated learning.
    rows = []
    for name, r in local.items():
        a = r["n"] / (r["n"] + BLEND_K)          # weight on the local model

        g = Ridge(alpha=1.0)
        g.coef_ = a * r["aligned"].coef_ + (1 - a) * coef
        g.intercept_ = a * r["aligned"].intercept_ + (1 - a) * intercept
        g.n_features_in_ = len(FEATURES)

        te = r["test"]
        Xg = g_scaler.transform(te[FEATURES])

        base = np.maximum(0, r["aligned"].predict(Xg))
        fed  = np.maximum(0, g.predict(Xg))

        m_base = mape(te["issues"].values, base)
        m_fed  = mape(te["issues"].values, fed)

        rows.append({
            "node": name,
            "train_rows": r["n"],
            "local_weight": round(a, 2),
            "local_mape": round(m_base, 2),
            "federated_mape": round(m_fed, 2),
            "improvement_%": round((m_base - m_fed) / m_base * 100, 1),
        })

    res = pd.DataFrame(rows)
    print(f"\n--- results ---")
    print(res.to_string(index=False))
    res.to_json(f"{OUT}/federation.json", orient="records", indent=2)

    best = res.loc[res["improvement_%"].idxmax()]
    print(f"\nLargest gain: {best['node']} — "
          f"{best['local_mape']}% -> {best['federated_mape']}% "
          f"({best['improvement_%']}% better)")
    print(f"\nsaved -> {OUT}/federation.json")


if __name__ == "__main__":
    main()