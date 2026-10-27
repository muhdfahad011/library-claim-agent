import os
import re
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()
H = {"Authorization": "Bearer " + os.getenv("FIRECRAWL_API_KEY")}
ISBN = "9780307278180"
SKIP = ("amazon.", "wikipedia.", "youtube.", "goodreads.", "facebook.", "reddit.")

r = requests.post("https://api.firecrawl.dev/v2/search", headers=H,
                  json={"query": f"{ISBN} buy paperback price", "limit": 8}, timeout=60)
print("search HTTP", r.status_code, "| retrieved", date.today().isoformat())
data = r.json().get("data", {})
rows = data.get("web", []) if isinstance(data, dict) else data
urls = [x["url"] for x in rows if not any(s in x["url"] for s in SKIP)][:3]
print("will scrape:", *urls, sep="\n  ")

pat = re.compile(r"(\$\s?\d[\d,]*\.\d\d|Rs\.?\s?\d[\d,]*|₹\s?\d[\d,]*|Paperback|Hardcover|Kindle|eBook|ISBN)", re.I)
for u in urls:
    s = requests.post("https://api.firecrawl.dev/v2/scrape", headers=H,
                      json={"url": u, "formats": ["markdown"]}, timeout=90)
    d = s.json().get("data", {})
    md = d.get("markdown") or ""
    print("\n==", u[:90])
    print("HTTP", s.status_code, "| title:", (d.get("metadata") or {}).get("title"), "| chars:", len(md))
    n = 0
    for line in md.splitlines():
        if pat.search(line) and n < 8:
            print("  |", line.strip()[:130])
            n += 1
