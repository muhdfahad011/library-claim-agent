import json, html
from datetime import date

p = json.load(open("claim_packet.json", encoding="utf-8"))
t = p["totals"]
e = html.escape
reasons = {}
for r in p["review_queue"]:
    reasons[r["ref_id"]] = r["reason"]

rows = []
for b in p["books"]:
    rc = b["replacement_cost"]
    if rc:
        price = f'{rc["amount"]:,} {rc["currency"]}'
        srcs = ", ".join(f'<a href="{e(s["url"])}">{i+1}</a>' for i, s in enumerate(rc["sources"]))
        note = "converted from " + "/".join(sorted({s["currency"] for s in rc["sources"]})) if rc.get("converted") else "local price"
    else:
        price, srcs, note = "not retrieved", "", "Firecrawl credits exhausted, so no page could be searched"
    flag = reasons.get(b["id"], "")
    cls = ' class="flag"' if flag else ""
    rows.append(f'<tr{cls}><td>{b["position"]}</td><td>{e(b["title"])}</td><td>{e(b["author"] or "unknown")}</td>'
                f'<td class="n">{price}</td><td>{note}</td><td>{srcs}</td><td>{e(flag)}</td></tr>')

fx = next((b["replacement_cost"].get("fx") for b in p["books"] if b["replacement_cost"] and b["replacement_cost"].get("fx")), None)
fx_line = f'Exchange rates from {e(fx["source"])} dated {e(fx["date"])} (USD to INR {fx["usd_inr"]:.2f}).' if fx else ""

css = ("body{font-family:Segoe UI,Arial,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#1a1a1a;background:#fff}"
       "@media(prefers-color-scheme:dark){body{color:#e8e8e8;background:#161616}a{color:#8ab4f8}}"
       "table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid #8884;padding:6px 8px;text-align:left;vertical-align:top}"
       "th{background:#8882}.n{text-align:right;white-space:nowrap}tr.flag{background:#ffcc0022}"
       ".box{display:flex;gap:1rem;flex-wrap:wrap}.card{border:1px solid #8886;border-radius:8px;padding:.6rem 1rem}"
       ".card b{font-size:1.4rem;display:block}")

page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Contents claim report</title><style>{css}</style></head><body>
<h1>Home library contents claim report</h1>
<p>Generated {date.today().isoformat()} from claim_packet.json. Country: {e(p["sweep"]["country"])}. Currency: {e(p["sweep"]["currency"])}.</p>
<div class="box">
<div class="card"><b>{t["book_count"]}</b>books counted</div>
<div class="card"><b>{t["books_priced"]}</b>books priced</div>
<div class="card"><b>{t["books_replacement_cost_inr"]:,} INR</b>total replacement cost (priced books)</div>
<div class="card"><b>{t["excluded_from_totals"]}</b>left out of the total</div>
<div class="card"><b>{t["books_in_review_queue"]}</b>need human review</div>
</div>
<h2>Basis of the numbers</h2>
<p>Each replacement cost is the median of prices read from retailer product pages (page links in the Sources column), retrieved on the date above. Prices are for a current printed copy and may differ from the exact edition on the shelf. Marketplace and ebook prices are never used. Where a price shows "not retrieved", the price lookup could not run because the Firecrawl credits were exhausted; no price was guessed. {fx_line} Rows highlighted in yellow are in the review queue. Totals are calculated in code, not by a language model.</p>
<h2>Inventory</h2>
<table><tr><th>#</th><th>Title</th><th>Author</th><th>Replacement cost</th><th>Price basis</th><th>Sources</th><th>Review reason</th></tr>
{"".join(rows)}
</table></body></html>"""
open("report.html", "w", encoding="utf-8").write(page)
print("saved report.html")
