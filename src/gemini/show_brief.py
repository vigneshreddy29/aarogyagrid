import json
c = json.load(open("data/processed/briefs.json", encoding="utf-8"))
for k, v in list(c.items())[:2]:
    print("=" * 70)
    print(f"{v['facility']} | {v['sku']} | {v['days_to_stockout']} days")
    print("-" * 70)
    print(v["english"])
    print("-" * 70)
    print(v["telugu"])
print("=" * 70)
