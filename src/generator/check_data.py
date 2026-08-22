import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd

led = pd.read_parquet("data/processed/stock_ledger.parquet")
dis = pd.read_parquet("data/processed/disease_weekly.parquet")

# monthly ORS issues vs monthly diarrhoeal cases, one district
d = "Nalgonda"

ors = led[(led.district == d) & (led.sku_code == "ORS001")].copy()
ors["month"] = pd.to_datetime(ors["date"]).dt.to_period("M")
ors_m = ors.groupby("month")["issues"].sum()

dia = dis[(dis.district == d) & (dis.disease == "diarrhoeal")].copy()
dia["month"] = pd.to_datetime(dia["week_start"]).dt.to_period("M")
dia_m = dia.groupby("month")["case_count"].sum()

comp = pd.DataFrame({"diarrhoeal_cases": dia_m, "ors_issued": ors_m}).dropna()
print(f"\n--- {d}: ORS vs diarrhoeal disease ---")
print(comp.to_string())
print(f"\nCORRELATION: {comp['diarrhoeal_cases'].corr(comp['ors_issued']):.3f}")

# stock-out concentration by district
print("\n--- stock-out days by district ---")
so = led[led.closing_stock == 0].groupby("district").size()
tot = led.groupby("district").size()
print(((so / tot) * 100).round(2).to_string(), "  (% of facility-SKU-days)")

# worst SKUs
print("\n--- stock-out days by SKU ---")
print(led[led.closing_stock == 0].groupby("sku_name").size().sort_values(ascending=False).to_string())