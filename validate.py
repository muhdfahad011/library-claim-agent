import json
import re
from difflib import SequenceMatcher

def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()

def title_score(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()

def author_ok(ocr_author, matched_authors):
    if not ocr_author or not matched_authors:
        return None  # unknown
    last = norm(ocr_author).split()[-1]
    return any(last in norm(a) for a in matched_authors)

data = json.load(open("enriched.json", encoding="utf-8"))
ok = 0
for b in data:
    m = b.get("match")
    reasons = []
    if not m:
        reasons.append("no match")
    else:
        ts = title_score(b["title"], m["matched_title"])
        b["title_score"] = round(ts, 2)
        if ts < 0.85:
            reasons.append(f"title mismatch ({ts:.2f})")
        if author_ok(b.get("author"), m.get("authors")) is False:
            reasons.append("author mismatch")
        if not m.get("isbn13"):
            reasons.append("no ISBN")
    b["status"] = "OK" if not reasons else "REVIEW"
    b["review_reasons"] = reasons
    ok += not reasons
    print(b["status"].ljust(7), b["title"][:40].ljust(40), "|", "; ".join(reasons))

print(f"\n{ok} OK, {len(data) - ok} need review")
json.dump(data, open("validated.json", "w", encoding="utf-8"), indent=2)
print("saved validated.json")
