import json
from datetime import datetime
import uuid

vals = json.load(open("validated.json", encoding="utf-8"))
prices = json.load(open("prices_final.json", encoding="utf-8"))

def fmt_class(f):
    return "hardcover" if "hard" in (f or "") else "paperback"

books, review = [], []
for i, b in enumerate(vals):
    m = b.get("match") or {}
    p = prices.get(str(i), {})
    rc = p.get("replacement_cost")
    flags = list(b.get("review_reasons", []))
    for f in p.get("review", []):
        if f != "mixed formats":
            flags.append(f)
    if rc and len({fmt_class(s["format"]) for s in rc["sources"]}) > 1:
        flags.append("mixed formats")
    bid = f"book-{i+1:03d}"
    books.append({
        "id": bid, "shelf": "", "position": i + 1, "frame_ref": "shelf.png",
        "status": "identified", "title": b["title"], "author": b.get("author") or "",
        "edition": "", "isbn": "", "isbn_candidate": m.get("isbn13") or "",
        "spine_height_cm": None, "spine_thickness_cm": None,
        "id_confidence": b.get("confidence"),
        "replacement_cost": rc, "used_value": None,
    })
    if flags:
        review.append({"ref_id": bid, "reason": "; ".join(flags)})

priced = [b for b in books if b["replacement_cost"]]
packet = {
    "sweep": {"id": uuid.uuid4().hex[:8], "captured_at": datetime.now().astimezone().isoformat(),
              "device": "", "duration_s": None, "country": "India (assumed, not yet confirmed)", "currency": "INR"},
    "room": {"length_m": None, "width_m": None, "height_m": None, "floor_area_m2": None,
             "wall_area_m2": None, "shelved_wall_area_m2": None, "scale_method": "", "confidence": None},
    "books": books, "items": [],
    "totals": {
        "book_count": len(books),
        "books_identified": sum(b["status"] == "identified" for b in books),
        "books_unidentified": sum(b["status"] == "unidentified" for b in books),
        "shelf_run_m": None,
        "books_replacement_cost_inr": sum(b["replacement_cost"]["amount"] for b in priced),
        "books_priced": len(priced),
        "books_in_review_queue": len({r["ref_id"] for r in review}),
        "excluded_from_totals": len(books) - len(priced),
        "books_used_value": 0,
    },
    "review_queue": review,
}
json.dump(packet, open("claim_packet.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(json.dumps(packet["totals"], indent=2))
print("\nfirst 3 review entries:")
for r in review[:3]:
    print(" ", r)
print("saved claim_packet.json")
