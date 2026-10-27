import json, statistics, requests
from urllib.parse import urlparse

d = json.load(open("prices.json", encoding="utf-8"))
j = requests.get("https://api.frankfurter.dev/v1/latest", params={"base": "USD", "symbols": "INR,GBP"}, timeout=30).json()
to_inr = {"INR": 1.0, "USD": j["rates"]["INR"], "GBP": j["rates"]["INR"] / j["rates"]["GBP"]}
fx = {"date": j["date"], "source": "https://api.frankfurter.dev/v1/latest?base=USD&symbols=INR,GBP",
      "usd_inr": to_inr["USD"], "gbp_inr": round(to_inr["GBP"], 4)}
print("FX date", fx["date"], "| USD->INR", round(to_inr["USD"], 2), "| GBP->INR", fx["gbp_inr"])

def cur(c):
    c = (c or "").strip().upper().replace(" ", "")
    if c in ("$", "US$", "USD"): return "USD"
    if c in ("\u20b9", "INR", "RS", "RS."): return "INR"
    if c in ("\u00a3", "GBP"): return "GBP"
    return None

def dom(u):
    return urlparse(u).netloc.lower().replace("www.", "")

out, total = {}, 0.0
for k, r in d.items():
    seen, srcs = set(), []
    for e in r.get("evidence", []):
        if e["kind"] != "replacement":
            continue
        x = e["extract"]
        c = cur(x["currency"])
        if not c or dom(e["url"]) in seen:
            continue
        seen.add(dom(e["url"]))
        srcs.append({"url": e["url"], "price": x["price_payable"], "currency": c,
                     "format": (x.get("format") or "").lower(), "retrieved_at": e["retrieved_at"]})
    flags = []
    local = [s for s in srcs if s["currency"] == "INR"]
    use, converted = (local, False) if local else (srcs, True)
    rec = None
    if use:
        vals = [s["price"] * to_inr[s["currency"]] for s in use]
        rec = {"amount": round(statistics.median(vals)), "currency": "INR", "converted": converted,
               "sources": [{"url": s["url"], "amount": s["price"], "currency": s["currency"], "format": s["format"]} for s in use],
               "retrieved_at": use[0]["retrieved_at"]}
        if converted:
            rec["fx"] = fx
        if len(use) < 2:
            flags.append("single source")
        if len(use) > 1 and max(vals) / min(vals) > 1.5:
            flags.append("sources differ by more than 50%")
        if len({s["format"] for s in use}) > 1:
            flags.append("mixed formats")
        if any("hard" in s["format"] for s in use):
            flags.append("hardcover price used")
        total += rec["amount"]
    else:
        flags.append("no verified replacement price")
    out[k] = {"title": r["title"], "replacement_cost": rec, "review": flags}
    print(r["title"][:34].ljust(34), (str(rec["amount"]) + " INR" + (" (conv)" if converted else " (local)")).ljust(18) if rec else "NONE".ljust(18), "|", len(use), "src |", ", ".join(flags))

json.dump(out, open("prices_final.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\npriced:", sum(1 for v in out.values() if v["replacement_cost"]), "/", len(out), "| total INR:", round(total))
print("saved prices_final.json")
