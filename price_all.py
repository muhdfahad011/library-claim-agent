import os, re, json, time, threading, statistics, requests
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()
COUNTRY, TARGET = "India", "INR"
MODEL = "gemini-3.5-flash-lite"
FC = {"Authorization": "Bearer " + os.getenv("FIRECRAWL_API_KEY")}
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
SKIP = ("amazon.", "wikipedia.", "youtube.", "goodreads.", "facebook.", "reddit.", "pinterest.", "instagram.", "jstor.")
MARKET = ("abebooks.", "ebay.", "biblio.", "alibris.", "thriftbooks.", "betterworldbooks.", "bookfinder.", "etsy.", "vitalsource.")
BAD_FORMATS = ("ebook", "kindle", "audio", "etext", "digital")
OUT = "prices.json"

class Extract(BaseModel):
    is_this_book: bool
    format: str | None
    price_type: str | None
    condition: str | None
    price_payable: float | None
    price_list: float | None
    currency: str | None
    quote: str | None

def norm(s):
    return re.sub(r"\s+", " ", (s or "")).lower().strip()

def extract(text, title, author):
    prompt = (
        f"Book: {title} by {author}.\n"
        "Using ONLY the page text below, find the price of a PRINTED copy (paperback or hardcover) of this exact book. "
        "is_this_book is true only for a product page of this exact book. Never use ebook, Kindle or audiobook prices. Never use shipping costs. "
        "price_payable is the price a buyer would actually pay today (the discounted price if one is shown). "
        "price_list is the full list price if shown, else null. "
        "price_type is one of: list, retail, marketplace_new, marketplace_used, other. condition is new, used or unknown. "
        "quote must be copied exactly from the page text (under 200 characters) and contain price_payable. "
        "If there is no clear printed-copy price, set price_payable to null.\n\nPAGE TEXT:\n" + text[:15000]
    )
    for _ in range(3):
        try:
            r = client.models.generate_content(model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Extract))
            return r.parsed
        except Exception:
            time.sleep(6)
    return None

def verify(ex, text):
    if not ex or not ex.is_this_book or ex.price_payable is None or not ex.quote:
        return False, "no price or not this book"
    if any(b in norm(ex.format) for b in BAD_FORMATS):
        return False, "ebook/audio format"
    if norm(ex.quote) not in norm(text):
        return False, "quote not found on page"
    nums = []
    for x in re.findall(r"\d[\d,]*\.?\d*", ex.quote):
        try: nums.append(float(x.replace(",", "").rstrip(".")))
        except ValueError: pass
    if ex.price_payable not in nums:
        return False, "price not in quote"
    return True, "ok"

def classify(url, ex):
    market = any(m in url for m in MARKET)
    if not market and ex.price_type in ("list", "retail") and ex.condition != "used":
        return "replacement"
    if market and ex.condition == "used" and ex.price_type == "marketplace_used":
        return "used"
    return "rejected: " + str(ex.price_type) + "/" + str(ex.condition) + (" marketplace" if market else "")

def lookup(title, author):
    q = f"{title} {author} paperback buy price {COUNTRY}"
    r = requests.post("https://api.firecrawl.dev/v2/search", headers=FC, json={"query": q, "limit": 8}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError("search HTTP %s: %s" % (r.status_code, r.text[:120]))
    data = r.json().get("data", {})
    rows = data.get("web", []) if isinstance(data, dict) else data
    urls = [x["url"] for x in rows if not any(s in x["url"] for s in SKIP)][:4]
    if not urls:
        raise RuntimeError("search returned no usable URLs")
    time.sleep(2)
    evidence = []
    for u in urls:
        text, err = "", None
        try:
            s = requests.post("https://api.firecrawl.dev/v2/scrape", headers=FC, json={"url": u, "formats": ["markdown"]}, timeout=90)
            if s.status_code != 200:
                err = "scrape HTTP %s" % s.status_code
            text = (s.json().get("data") or {}).get("markdown") or ""
        except Exception as e:
            err = "scrape failed: " + str(e)[:60]
        time.sleep(1)
        ex = extract(text, title, author) if len(text) > 200 else None
        if err or (len(text) > 200 and ex is None):
            evidence.append({"url": u, "kind": "error: " + (err or "model call failed"), "retrieved_at": date.today().isoformat(), "extract": None})
            continue
        ok, why = verify(ex, text)
        kind = classify(u, ex) if ok else "rejected: " + why
        evidence.append({"url": u, "kind": kind, "retrieved_at": date.today().isoformat(),
                         "extract": ex.model_dump() if ex else None})
    if evidence and all(e["kind"].startswith("error") for e in evidence):
        raise RuntimeError("all pages errored: " + evidence[0]["kind"])
    rep = [e for e in evidence if e["kind"] == "replacement"]
    used = [e for e in evidence if e["kind"] == "used"]
    review = []
    out = {"title": title, "evidence": evidence, "replacement_cost": None, "used_value": None, "review": review}
    if rep:
        vals = [e["extract"]["price_payable"] for e in rep]
        out["replacement_cost"] = {"amount": statistics.median(vals), "currency": rep[0]["extract"]["currency"] or "USD",
            "sources": [e["url"] for e in rep], "retrieved_at": date.today().isoformat(), "converted": False,
            "range": [min(vals), max(vals)]}
        if len(rep) < 2:
            review.append("only one replacement price source")
        if max(vals) / min(vals) > 1.5:
            review.append("replacement sources disagree by more than 50%")
    else:
        review.append("no verified replacement price")
    if used:
        vals = [e["extract"]["price_payable"] for e in used]
        out["used_value"] = {"amount": statistics.median(vals), "currency": used[0]["extract"]["currency"] or "USD",
            "sources": [e["url"] for e in used], "retrieved_at": date.today().isoformat(),
            "condition_assumed": used[0]["extract"]["condition"], "converted": False}
    return out

books = json.load(open("validated.json", encoding="utf-8"))
done = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
lock = threading.Lock()

def work(i):
    key = str(i)
    if key in done and "error" not in done[key] and done[key].get("replacement_cost"):
        return
    b = books[i]
    try:
        res = lookup(b["title"], b.get("author") or "")
    except Exception as e:
        res = {"title": b["title"], "error": str(e)[:200]}
    with lock:
        done[key] = res
        json.dump(done, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    rc = (res.get("replacement_cost") or {}).get("amount")
    print(f"[{i+1}/{len(books)}] {b['title'][:38].ljust(38)} replacement: {rc} | {res.get('review') or res.get('error')}", flush=True)

with ThreadPoolExecutor(max_workers=1) as ex:
    list(ex.map(work, range(len(books))))

fx = None
try:
    j = requests.get("https://api.frankfurter.dev/v1/latest", params={"base": "USD", "symbols": TARGET}, timeout=30).json()
    fx = {"rate": j["rates"][TARGET], "date": j["date"],
          "source": f"https://api.frankfurter.dev/v1/latest?base=USD&symbols={TARGET}"}
    print("\nFX USD->%s: %s on %s" % (TARGET, fx["rate"], fx["date"]))
except Exception as e:
    print("\nFX lookup FAILED, keeping USD amounts:", str(e)[:100])

for key, res in done.items():
    for field in ("replacement_cost", "used_value"):
        v = res.get(field)
        if v and v["currency"] == "USD" and not v.get("converted"):
            if fx:
                v["original_amount"], v["original_currency"] = v["amount"], "USD"
                v["amount"] = round(v["amount"] * fx["rate"])
                v["currency"], v["converted"] = TARGET, True
                v["fx_rate"], v["fx_date"], v["fx_source"] = fx["rate"], fx["date"], fx["source"]
            else:
                res["review"].append("not converted: no FX rate")
json.dump(done, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

priced = sum(1 for r in done.values() if r.get("replacement_cost"))
flagged = sum(1 for r in done.values() if r.get("review"))
print(f"\nbooks priced: {priced}/{len(books)} | with review flags: {flagged}")
print("saved", OUT)
