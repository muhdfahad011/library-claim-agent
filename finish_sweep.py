import json, glob, os, sys, html, uuid
from datetime import datetime

base = sys.argv[1] if len(sys.argv) > 1 else None
if base is None:
    cands = [d for d in sorted(glob.glob("live/sweeps/*")) if os.path.exists(os.path.join(d, "inventory.json"))]
    if not cands:
        raise SystemExit("no sweep folder with inventory.json found under live/sweeps")
    base = cands[-1]
inv = json.load(open(os.path.join(base, "inventory.json"), encoding="utf-8"))
frames = json.load(open(os.path.join(base, "frames.json"), encoding="utf-8"))["frames"]
cache = json.load(open("price_cache.json", encoding="utf-8")) if os.path.exists("price_cache.json") else {}
REASON = "price lookup not run: Firecrawl credits exhausted"
import re as _re
_mp = os.path.join(base, "measurements.json")
_ip = os.path.join(base, "items.json")
_meas = json.load(open(_mp, encoding="utf-8")) if os.path.exists(_mp) else None
_items = json.load(open(_ip, encoding="utf-8")) if os.path.exists(_ip) else []


def _tk(s):
    return set(w for w in _re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).split() if len(w) > 1)


def _find(title):
    if not _meas:
        return None
    best, bs = None, 0
    a = _tk(title)
    for m in _meas["books"]:
        b = _tk(m["title"])
        sc = len(a & b) / max(len(a), len(b)) if a and b else 0
        if sc > bs:
            best, bs = m, sc
    return best if bs >= 0.6 else None


def mh(title):
    m = _find(title)
    return None if (not m or m.get("is_reference")) else m["height_cm"]


def mt(title):
    m = _find(title)
    return m["thickness_cm"] if m else None


items_out = []
for _i, _x in enumerate(_items, 1):
    items_out.append({"id": "item-%03d" % _i, "category": _x["category"], "description": _x["description"],
                      "brand_model": _x.get("brand_model") or "", "frame_ref": _x["frame_ref"],
                      "dimensions_cm": {"w": None, "h": None, "d": None},
                      "status": "needs_appraisal" if _x["is_art"] else "unpriced",
                      "replacement_cost": None, "confidence": _x["confidence"]})
scale_text = ("reference book of known height (%s, %s cm, supplied by the user); same-plane assumption"
              % (_meas["reference"]["title"], _meas["reference"]["height_cm"])) if _meas else ""

def key(t):
    return " ".join("".join(c for c in t.lower() if c.isalnum() or c == " ").split())

books, review = [], []
for i, b in enumerate(inv, 1):
    c = cache.get(key(b["title"])) or {}
    rc = c.get("replacement_cost")
    bid = "book-%03d" % i
    books.append({
        "id": bid, "shelf": "", "position": i, "frame_ref": b["frame_ref"],
        "status": "identified", "title": b["title"], "author": b.get("author") or "",
        "edition": "", "isbn": "",
        "spine_height_cm": mh(b["title"]), "spine_thickness_cm": mt(b["title"]),
        "id_confidence": b["id_confidence"],
        "replacement_cost": rc, "used_value": None,
    })
    reasons = []
    if not rc:
        reasons.append(c.get("reason") or REASON)
    if mh(b["title"]) is None and mt(b["title"]) is None:
        reasons.append("not measured in this sweep")
    else:
        reasons.append("thickness unreliable: failed the 15% pass bar in testing")
    if b["id_confidence"] < 0.9:
        reasons.append("low identification confidence")
    review.append({"ref_id": bid, "reason": "; ".join(reasons)})

for _it in items_out:
    _r = "price not retrieved: Firecrawl credits exhausted"
    if _it["status"] == "needs_appraisal":
        _r = "art or portrait: needs appraisal (ask whether it is an original or a print); " + _r
    review.append({"ref_id": _it["id"], "reason": _r})
review.append({"ref_id": "sweep", "reason": "room area not measured (skipped); other-item sizes not measured"})

priced = [b for b in books if b["replacement_cost"]]
currencies = {b["replacement_cost"]["currency"] for b in priced}
total = sum(b["replacement_cost"]["amount"] for b in priced) if (priced and len(currencies) == 1) else None
duration = frames[-1]["t_s"] if frames else 0

packet = {
    "sweep": {"id": uuid.uuid4().hex[:8], "captured_at": datetime.now().astimezone().isoformat(),
              "device": "", "duration_s": duration, "country": "", "currency": ""},
    "room": {"length_m": None, "width_m": None, "height_m": None, "floor_area_m2": None,
             "wall_area_m2": None, "shelved_wall_area_m2": None, "scale_method": scale_text, "confidence": None},
    "books": books, "items": items_out,
    "totals": {"book_count": len(books), "books_identified": len(books), "books_unidentified": 0,
               "shelf_run_m": None, "books_replacement_cost": total, "books_used_value": None,
               "items_replacement_cost_low": None, "items_replacement_cost_high": None,
               "excluded_from_totals": len(books) - len(priced)},
    "review_queue": review,
}
json.dump(packet, open(os.path.join(base, "claim_packet.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)

e = html.escape
rev = {r["ref_id"]: r["reason"] for r in review}
rows = []
for b in books:
    rc = b["replacement_cost"]
    price = "%s %s" % (rc["amount"], rc["currency"]) if rc else "not retrieved"
    link = '<a href="%s">frame</a>' % e(os.path.basename(b["frame_ref"]))
    rows.append("<tr class='flag'><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        b["position"], e(b["title"]), e(b["author"] or "unknown"), e(price), link, e(rev[b["id"]])))
css = ("body{font-family:Segoe UI,Arial,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#1a1a1a;background:#fff}"
       "@media(prefers-color-scheme:dark){body{color:#e8e8e8;background:#161616}a{color:#8ab4f8}}"
       "table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid #8884;padding:6px 8px;text-align:left;vertical-align:top}"
       "th{background:#8882}tr.flag{background:#ffcc0018}")
t = packet["totals"]
page = ("<!doctype html><html><head><meta charset='utf-8'><title>Contents claim report</title><style>%s</style></head><body>"
        "<h1>Home library contents claim report</h1><p>Generated %s from claim_packet.json. Sweep length %.0f s. Country and currency were not recorded.</p>"
        "<p><b>%d</b> books logged, <b>%d</b> priced, <b>%d</b> left out of the total. Total replacement cost: <b>%s</b>.</p>"
        "<h2>Basis of the numbers</h2><p>Titles were read from saved camera frames (the frame link opens the image). "
        "Where a price shows not retrieved, the price lookup could not run because the Firecrawl credits were exhausted; no price was guessed. "
        "Spine sizes, room area and non-book items were not measured in this sweep. Totals are calculated in code, not by a language model.</p>"
        "<table><tr><th>#</th><th>Title</th><th>Author</th><th>Replacement cost</th><th>Evidence</th><th>Review reason</th></tr>%s</table>"
        "<p>%s</p></body></html>") % (css, datetime.now().strftime("%Y-%m-%d"), duration, t["book_count"], len(priced),
                                     t["excluded_from_totals"], total if total is not None else "not available", "".join(rows),
                                     e(review[-1]["reason"]))
open(os.path.join(base, "report.html"), "w", encoding="utf-8").write(page)

print("sweep folder:", base)
print("books logged:", len(books), "| priced:", len(priced), "| in review queue:", len(review) - 1)
print("summary to read aloud: I logged %d books. %d have prices and %d need review. Room area and spine sizes were not measured in this sweep." % (len(books), len(priced), len(books) - len(priced)))
print("saved claim_packet.json and report.html in", base)

_rp = os.path.join(base, "report.html")
_h = open(_rp, encoding="utf-8").read()
_h = _h.replace("Spine sizes, room area and non-book items were not measured in this sweep.",
                "Room area was not measured (skipped). Spine sizes use a reference book of known height; thickness is unreliable and failed the 15% pass bar in testing. Other contents were detected from the frames; their sizes and prices were not retrieved.")
_rows = []
for _b in books:
    _m = _find(_b["title"])
    if _m and _m.get("is_reference"):
        _hh = "reference (height supplied)"
    else:
        _hh = "" if _b["spine_height_cm"] is None else str(_b["spine_height_cm"]) + " cm"
    _tt = "" if _b["spine_thickness_cm"] is None else str(_b["spine_thickness_cm"]) + " cm"
    _rows.append("<tr><td>" + str(_b["position"]) + "</td><td>" + e(_b["title"]) + "</td><td>" + _hh + "</td><td>" + _tt + "</td></tr>")
_irows = []
for _it in items_out:
    _irows.append("<tr><td>" + e(_it["category"]) + "</td><td>" + e(_it["description"]) + "</td><td>" + e(_it["status"]) + "</td><td><a href=" + chr(34) + e(os.path.basename(_it["frame_ref"])) + chr(34) + ">frame</a></td></tr>")
_extra = ("<h2>Spine sizes</h2><p>Scale: " + e(scale_text or "not available") + ". Thickness is unreliable.</p>"
          "<table><tr><th>#</th><th>Title</th><th>Height</th><th>Thickness</th></tr>" + "".join(_rows) + "</table>"
          "<h2>Other contents</h2><p>Sizes and prices were not retrieved. Art and portraits need appraisal.</p>"
          "<table><tr><th>Category</th><th>Description</th><th>Status</th><th>Evidence</th></tr>" + "".join(_irows) + "</table>")
_h = _h.replace("</body></html>", _extra + "</body></html>")
open(_rp, "w", encoding="utf-8").write(_h)
print("added spine sizes and other contents to the report:", len(items_out), "items")
