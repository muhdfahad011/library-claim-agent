import shutil
shutil.copy("finish_sweep.py", "finish_sweep.py.bak")


def swap(s, old, new):
    n = s.count(old)
    assert n == 1, "anchor found %d times: %s" % (n, old[:60])
    return s.replace(old, new)


BLOCK = r"""REASON = "price lookup not run: Firecrawl credits exhausted"
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
"""

NEWREASON = r"""    if mh(b["title"]) is None and mt(b["title"]) is None:
        reasons.append("not measured in this sweep")
    else:
        reasons.append("thickness unreliable: failed the 15% pass bar in testing")
"""

SWEEPREVIEW = r"""for _it in items_out:
    _r = "price not retrieved: Firecrawl credits exhausted"
    if _it["status"] == "needs_appraisal":
        _r = "art or portrait: needs appraisal (ask whether it is an original or a print); " + _r
    review.append({"ref_id": _it["id"], "reason": _r})
review.append({"ref_id": "sweep", "reason": "room area not measured (skipped); other-item sizes not measured"})"""

EXTRA = r"""
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
"""

s = open("finish_sweep.py", encoding="utf-8").read()
s = swap(s, 'REASON = "price lookup not run: Firecrawl credits exhausted"', BLOCK.rstrip("\n"))
s = swap(s, '"spine_height_cm": None, "spine_thickness_cm": None,',
         '"spine_height_cm": mh(b["title"]), "spine_thickness_cm": mt(b["title"]),')
s = swap(s, '    reasons.append("not measured in this sweep")\n', NEWREASON)
s = swap(s, '"books": books, "items": [],', '"books": books, "items": items_out,')
s = swap(s, '"scale_method": "", "confidence": None},', '"scale_method": scale_text, "confidence": None},')
s = swap(s, 'review.append({"ref_id": "sweep", "reason": "room area not measured; non-book items not captured; spine sizes not measured"})', SWEEPREVIEW)
s = s.rstrip("\n") + "\n" + EXTRA
open("finish_sweep.py", "w", encoding="utf-8").write(s)
print("patched finish_sweep.py (backup: finish_sweep.py.bak)")
