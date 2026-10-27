import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"

class Price(BaseModel):
    index: int
    price_usd: float | None
    format: str | None
    confidence: float

data = json.load(open("validated.json", encoding="utf-8"))
lines = []
for i, b in enumerate(data):
    m = b.get("match") or {}
    lines.append(f'{i}. "{b["title"]}" by {b.get("author")} (first published {m.get("first_published")})')

prompt = (
    "Estimate the typical current US retail list price in USD of a NEW copy "
    "(paperback unless it is hardcover-only) of each book below. Use only your "
    "own knowledge. If you are unsure, give your best estimate with a LOW "
    "confidence (0 to 1) instead of refusing. Return one entry per book using "
    "the same index.\n\n" + "\n".join(lines)
)

resp = client.models.generate_content(
    model=MODEL,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=list[Price],
    ),
)
prices = {p["index"]: p for p in json.loads(resp.text)}

total = 0.0
for i, b in enumerate(data):
    p = prices.get(i, {})
    b["valuation"] = {
        "price_usd": p.get("price_usd"),
        "format": p.get("format"),
        "confidence": p.get("confidence"),
        "source": "model_estimate",
    }
    total += p.get("price_usd") or 0
    print(b["title"][:40].ljust(40), "|", p.get("price_usd"), "|",
          p.get("format"), "|", p.get("confidence"))

print(f"\nEstimated total replacement value: ${total:,.2f}")
json.dump(data, open("valued.json", "w", encoding="utf-8"), indent=2)
print("saved valued.json")
