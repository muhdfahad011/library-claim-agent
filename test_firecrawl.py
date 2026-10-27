import os
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()
r = requests.post(
    "https://api.firecrawl.dev/v2/search",
    headers={"Authorization": "Bearer " + os.getenv("FIRECRAWL_API_KEY")},
    json={"query": "1491 Charles C. Mann paperback price amazon.in", "limit": 5},
    timeout=60,
)
print("HTTP", r.status_code, "| retrieved", date.today().isoformat())
body = r.json()
data = body.get("data", body)
rows = data.get("web", []) if isinstance(data, dict) else data
for x in rows:
    print("-", (x.get("title") or "")[:70])
    print("  ", x.get("url"))
    print("  ", (x.get("description") or "")[:150])
if not rows:
    print(str(body)[:400])
