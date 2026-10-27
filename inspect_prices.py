import json
d = json.load(open("prices.json", encoding="utf-8"))
for k, r in d.items():
    rc = r.get("replacement_cost") or {}
    if rc.get("amount") and (rc["amount"] > 40 or any("disagree" in x for x in r.get("review", []))):
        print("\n##", r["title"], "| median:", rc["amount"], rc.get("currency"))
        for e in r["evidence"]:
            if e["kind"] == "replacement":
                x = e["extract"]
                print("   ", x["price_payable"], x["currency"], x["format"], "|", e["url"][:70])
