import os, re, json, time, requests
from datetime import date
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()
COUNTRY, CURRENCY = "India", "INR"
MODEL = "gemini-3.5-flash-lite"
FC = {"Authorization": "Bearer " + os.getenv("FIRECRAWL_API_KEY")}
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
SKIP = ("amazon.", "wikipedia.", "youtube.", "goodreads.", "facebook.", "reddit.", "pinterest.", "instagram.")
BAD_FORMATS = ("ebook", "kindle", "audio", "etext")

class Extract(BaseModel):
    is_this_book: bool
    format: str | None
    price: float | None
    currency: str | None
    quote: str | None

def norm(s):
    return re.sub(r"\s+", " ", (s or "")).lower().strip()

def extract(text, title, author):
    prompt = (
        f"Book: {title} by {author}. Country: {COUNTRY}.\n"
        "Using ONLY the page text below, find the selling price of a PRINTED copy "
        "(paperback or hardcover) of this exact book. is_this_book is true only if the page "
        "is a product page for this exact book. Never use ebook, Kindle or audiobook prices. "
        "quote must be copied exactly from the page text (under 200 characters) and contain the price. "
        "If there is no printed-copy price, set price to null.\n\nPAGE TEXT:\n" + text[:15000]
    )
    for attempt in range(3):
        try:
            r = client.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Extract))
            return r.parsed
        except Exception as e:
            time.sleep(5)
    return None

def verify(ex, text):
    if not ex or not ex.is_this_book or ex.price is None or not ex.quote:
        return False, "no price or not this book"
    if any(b in norm(ex.format) for b in BAD_FORMATS):
        return False, "ebook/audio format"
    if norm(ex.quote) not in norm(text):
        return False, "quote not found on page"
    nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", ex.quote) if x.replace(",", "").replace(".", "").isdigit()]
    if ex.price not in nums:
        return False, "price not in quote"
    return True, "ok"

def lookup(title, author):
    q = f"{title} {author} paperback buy price {COUNTRY}"
    r = requests.post("https://api.firecrawl.dev/v2/search", headers=FC, json={"query": q, "limit": 8}, timeout=60)
    data = r.json().get("data", {})
    rows = data.get("web", []) if isinstance(data, dict) else data
    urls = [x["url"] for x in rows if not any(s in x["url"] for s in SKIP)][:3]
    out = []
    for u in urls:
        s = requests.post("https://api.firecrawl.dev/v2/scrape", headers=FC, json={"url": u, "formats": ["markdown"]}, timeout=90)
        text = (s.json().get("data") or {}).get("markdown") or ""
        ex = extract(text, title, author) if len(text) > 200 else None
        ok, why = verify(ex, text)
        out.append({"url": u, "verified": ok, "why": why, "retrieved_at": date.today().isoformat(),
                    "country": COUNTRY, "extract": ex.model_dump() if ex else None})
    return out

tests = [("1491", "Charles C. Mann"), ("Cobalt Red", "Siddharth Kara"), ("King Leopold's Ghost", "Adam Hochschild")]
results = {}
for t, a in tests:
    res = lookup(t, a)
    results[t] = res
    print("\n##", t)
    for x in res:
        e = x["extract"] or {}
        print(" ", "OK  " if x["verified"] else "NO  ", x["url"][:70])
        print("      ", e.get("format"), e.get("price"), e.get("currency"), "|", x["why"])
json.dump(results, open("price_test.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\nsaved price_test.json")
