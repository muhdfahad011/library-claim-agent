import os
import re
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()
URL = "https://www.amazon.com/1491-Revelations-Americas-Before-Columbus/dp/140004006X"
r = requests.post(
    "https://api.firecrawl.dev/v2/scrape",
    headers={"Authorization": "Bearer " + os.getenv("FIRECRAWL_API_KEY")},
    json={"url": URL, "formats": ["markdown"]},
    timeout=90,
)
print("HTTP", r.status_code, "| retrieved", date.today().isoformat())
body = r.json()
data = body.get("data", {})
md = data.get("markdown") or ""
print("page title:", (data.get("metadata") or {}).get("title"))
print("markdown chars:", len(md))
if not md:
    print(str(body)[:400])
pat = re.compile(r"(\$\s?\d[\d,]*\.?\d*|Paperback|Hardcover|Kindle|ISBN-13|List Price|Print List)", re.I)
shown = 0
for line in md.splitlines():
    if pat.search(line) and shown < 15:
        print("|", line.strip()[:140])
        shown += 1
