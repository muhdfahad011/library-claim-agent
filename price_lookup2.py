import os, re, json, time, statistics, requests
from datetime import date
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()
COUNTRY = "India"
MODEL = "gemini-3.5-flash-lite"
FC = {"Authorization": "Bearer " + os.getenv("FIRECRAWL_API_KEY")}
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
SKIP = ("amazon.", "wikipedia.", "youtube.", "goodreads.", "facebook.", "reddit.", "pinterest.", "instagram.", "jstor.")
MARKET = ("abebooks.", "ebay.", "biblio.", "alibris.", "thriftbooks.", "betterworldbooks.", "bookfinder.", "etsy.", "vitalsource.")
BAD_FORMATS = ("ebook", "kindle", "audio", "etext", "digital")

class Extract(BaseModel):
    is_this_book: bool
    format: str | None
    price_type: str | None   # list, retail, marketplace_new, marketplace_used, other
    condition: str | None    # new, used, unknown
    price: float | None
    currency: str | None
    quote: str | None

def norm(s):
    return re.sub(r"\s+", " ", (s or "")).lower().strip()

def extract(text, title, author):
    prompt = (
        f"Book: {title} by {author}.\n"
        "Using ONLY the page text below, find ONE price for a PRINTED copy (paperback or hardcover) of this exact book. "
        "is_this_book is true only for a product page of this exact book. Never use ebook, Kindle or audiobook prices. "
        "Never use shipping costs. price_type is one of: list, retail, marketplace_new, marketplace_used, other. "
        "condition is new, used or unknown. quote must be copied exactly from the page text (under 200 characters) and contain the price. "
        "If there is no clear printed-copy price, set price to null.\n\nPAGE TEXT:\n" + text[:15000]
    )
    for _ in range(3):
        try:
            r = client.models.generate_content(model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Extract))
            return r.parsed
        except Exception:
            time.sleep(5)
    return None

def verify(ex, text):
    if not ex or not ex.is_this_book or ex.price is None or not ex.quote:
        return False, "no price or not this book"
    if any(b in norm(ex.format) for b in BAD_FORMATS):
        return False, "ebook/audio format"
    if norm(ex.quote) not in norm(text):
        return False, "quote not found on page"
    nums = []
    for x in re.findall(r"\d[\d,]*\.?\d*", ex.quote):
        try: nums.append(float(x.replace(",", "").rstrip(".")))
        except ValueError: pass
    if ex.price not in nums:
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
    data = r.json().get("data", {})
    rows = data.get("web", []) if isinstance(data, dict) else data
    urls = [x["url"] for x in rows if not any(s in x["url"] for s in SKIP)][:4]
    evidence = []
    for u in urls:
        s = requests.post("https://api.firecrawl.dev/v2/scrape", headers=FC, json={"url": u, "formats": ["markdown"]}, timeout=90)
        text = (s.json().get("data") or {}).get("markdown") or ""
        ex = extract(text, title, author) if len(text) > 200 else None
        ok, why = verify(ex, text)
        kind = classify(u, ex) if ok else "rejected: " + why
        evidence.append({"url": u, "kind": kind, "retrieved_at": date.today().isoformat(),
                         "extract": ex.model_dump() if ex else None})
    rep = [e for e in evidence if e["kind"] == "replacement"]
    used = [e for e in evidence if e["kind"] == "used"]
    review = []
    out = {"title": title, "evidence": evidence, "replacement_cost": None, "used_value": None, "review": review}
    if rep:
        vals = [e["extract"]["price"] for e in rep]
        med = statistics.median(vals)
        out["replacement_cost"] = {"amount": med, "currency": rep[0]["extract"]["currency"], "sources": [e["url"] for e in rep],
                                   "retrieved_at": date.today().isoformat(), "converted": False, "range": [min(vals), max(vals)]}
        if max(vals) / min(vals) > 1.25:
            review.append("replacement sources disagree by more than 25%")
    else:
        review.append("no verified replacement price")
    if used:
        vals = [e["extract"]["price"] for e in used]
        out["used_value"] = {"amount": statistics.median(vals), "currency": used[0]["extract"]["currency"],
                             "sources": [e["url"] for e in used], "retrieved_at": date.today().isoformat(),
                             "condition_assumed": used[0]["extract"]["condition"]}
    return out

tests = [("1491", "Charles C. Mann"), ("Cobalt Red", "Siddharth Kara"), ("King Leopold's Ghost", "Adam Hochschild")]
results = []
for t, a in tests:
    res = lookup(t, a)
    results.append(res)
    print("\n##", t)
    for e in res["evidence"]:
        x = e["extract"] or {}
        print("  ", e["kind"].ljust(40), x.get("price"), x.get("currency"), "|", e["url"][:60])
    print("   => replacement:", (res["replacement_cost"] or {}).get("amount"), "| used:", (res["used_value"] or {}).get("amount"), "| review:", res["review"])
json.dump(results, open("price_test2.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\nsaved price_test2.json")
