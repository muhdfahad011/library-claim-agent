import os, requests
from dotenv import load_dotenv
from google import genai
load_dotenv()

print("CHECK 1: search for a book that got zero pages (Wake)")
r = requests.post("https://api.firecrawl.dev/v2/search",
    headers={"Authorization": "Bearer " + os.getenv("FIRECRAWL_API_KEY")},
    json={"query": "Wake Rebecca Hall paperback buy price India", "limit": 5}, timeout=60)
print("HTTP", r.status_code)
print(r.text[:300])

print("\nCHECK 2: one Gemini call with the same model the price script uses")
try:
    c = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    out = c.models.generate_content(model="gemini-3.5-flash-lite", contents="Say hi")
    print("OK:", out.text[:60])
except Exception as e:
    print(type(e).__name__, str(e)[:300])
