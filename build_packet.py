import json
import uuid
from datetime import datetime

data = json.load(open("validated.json", encoding="utf-8"))
books, review = [], []

for i, b in enumerate(data, start=1):
    m = b.get("match") or {}
    ok = b.get("status") == "OK"
    bid = f"book-{i:03d}"
    books.append({
        "id": bid, "shelf": "", "position": i, "frame_ref": "shelf.png",
        "status": "identified",
        "title": b["title"], "author": b.get("author") or "",
        "edition": "", "isbn": (m.get("isbn13") or "") if ok else "",
        "spine_height_cm": None, "spine_thickness_cm": None,
        "id_confidence": b.get("confidence"),
        "replacement_cost": None, "used_value": None,
    })
    reasons = ["no sourced price"] + list(b.get("review_reasons", []))
    review.append({"ref_id": bid, "reason": "; ".join(reasons)})

priced = [b for b in books if b["replacement_cost"]]
packet = {
    "sweep": {"id": uuid.uuid4().hex[:8], "captured_at": datetime.now().astimezone().isoformat(),
              "device": "", "duration_s": None, "country": "", "currency": ""},
    "room": {"length_m": None, "width_m": None, "height_m": None, "floor_area_m2": None,
             "wall_area_m2": None, "shelved_wall_area_m2": None, "scale_method": "", "confidence": None},
    "books": books,
    "items": [],
    "totals": {
        "book_count": len(books),
        "books_identified": sum(b["status"] == "identified" for b in books),
        "books_unidentified": sum(b["status"] == "unidentified" for b in books),
        "shelf_run_m": None,
        "books_replacement_cost": sum(b["replacement_cost"]["amount"] for b in priced),
        "books_used_value": sum(b["used_value"]["amount"] for b in books if b["used_value"]),
        "items_replacement_cost_low": 0, "items_replacement_cost_high": 0,
        "excluded_from_totals": len(books) - len(priced),
    },
    "review_queue": review,
}
json.dump(packet, open("claim_packet.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("saved claim_packet.json")
print(json.dumps(packet["totals"], indent=2))
