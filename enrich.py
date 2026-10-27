import json
import time
import requests

HEADERS = {"User-Agent": "LibraryClaimAgent/0.1 (take-home project)"}
FIELDS = "key,title,author_name,first_publish_year,publisher,isbn"

def search(title, author):
    params = {"title": title, "limit": 1, "fields": FIELDS}
    if author:
        params["author"] = author
    r = requests.get("https://openlibrary.org/search.json",
                     params=params, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return None, r.status_code
    docs = r.json().get("docs", [])
    return (docs[0] if docs else None), r.status_code

books = json.load(open("books.json", encoding="utf-8"))
enriched = []

for b in books:
    doc, status = search(b["title"], b.get("author"))
    if doc is None and b.get("author"):
        doc, status = search(b["title"], None)
    entry = dict(b)
    entry["match"] = None
    if doc:
        isbn13 = next((i for i in doc.get("isbn", []) if len(i) == 13), None)
        entry["match"] = {
            "matched_title": doc.get("title"),
            "authors": doc.get("author_name"),
            "publisher": (doc.get("publisher") or [None])[0],
            "first_published": doc.get("first_publish_year"),
            "isbn13": isbn13,
            "ol_key": doc.get("key"),
        }
    else:
        entry["lookup_status"] = status
    enriched.append(entry)
    m = entry["match"]
    print(b["title"][:38].ljust(38), "|",
          (m["matched_title"][:30] if m else "NO MATCH"), "|",
          (m["first_published"] if m else status), "|",
          (m["isbn13"] if m else ""))
    time.sleep(1)

json.dump(enriched, open("enriched.json", "w", encoding="utf-8"), indent=2)
print("saved enriched.json")
