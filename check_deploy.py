import pandas as pd, subprocess

a = pd.read_parquet("data/processed/alerts.parquet")
print("--- local alerts.parquet ---")
print(a.tier.value_counts().to_string())

print("\n--- git status for that file ---")
print(subprocess.run(["git", "status", "--short", "data/processed/alerts.parquet"],
                     capture_output=True, text=True).stdout or "(clean — matches committed version)")

print("\n--- disease_weekly dtypes (Why It Works uses these) ---")
d = pd.read_parquet("data/processed/disease_weekly.parquet")
print(d.dtypes.to_string())
print("districts:", list(d.district.unique()))

print("\n--- ledger dtypes ---")
l = pd.read_parquet("data/processed/stock_ledger.parquet")
print(l[["date", "district", "sku_code"]].dtypes.to_string())