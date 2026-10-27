import os, json, time, statistics
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"

class Group(BaseModel):
    category: str
    name: str
    indices: list[int]

class Groups(BaseModel):
    groups: list[Group]

items = json.load(open("items_found.json", encoding="utf-8"))
lines = []
for i, x in enumerate(items):
    size = f'{x.get("approx_width_cm")}x{x.get("approx_height_cm")}cm'
    lines.append(f'{i}. [{x["category"]}] {x["description"]} | size {size} | first seen {x["frame_ref"]}')

prompt = (
    "Below are object detections from different frames of ONE video of ONE room. The same physical object often appears several times "
    "with different wording. Group detections that are the same physical object. Different objects (for example two different maps or "
    "two different shelves) must stay in separate groups. Every index must appear in exactly one group. For each group give a short name "
    "and ONE clean category chosen from: shelving, furniture, framed art, decor, electronics, lighting, rug, appliance, other.\n\n"
    + "\n".join(lines)
)

res, last = None, ""
for _ in range(4):
    try:
        r = client.models.generate_content(model=MODEL, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Groups))
        res = r.parsed
        break
    except Exception as e:
        last = str(e)[:150]
        time.sleep(8)
if res is None:
    raise SystemExit("merge call failed: " + last)

used, groups = set(), []
for g in res.groups:
    idx = [i for i in g.indices if 0 <= i < len(items) and i not in used]
    used.update(idx)
    if idx:
        groups.append((g, idx))
for i in range(len(items)):
    if i not in used:
        groups.append((Group(category=items[i]["category"], name=items[i]["description"][:40], indices=[i]), [i]))

merged = []
for g, idx in groups:
    members = [items[i] for i in idx]
    w = [m["approx_width_cm"] for m in members if m.get("approx_width_cm")]
    h = [m["approx_height_cm"] for m in members if m.get("approx_height_cm")]
    art = sum(1 for m in members if m.get("is_art_or_portrait")) > len(members) / 2
    brand = next((m["brand_model"] for m in members if m.get("brand_model")), None)
    seen = sorted({f for m in members for f in m["seen_in"]})
    cat = g.category.lower()
    merged.append({
        "category": cat, "description": g.name, "brand_model": brand,
        "approx_width_cm": round(statistics.median(w)) if w else None,
        "approx_height_cm": round(statistics.median(h)) if h else None,
        "frame_ref": members[0]["frame_ref"], "seen_in": seen, "detections_merged": len(members),
        "status": "needs_appraisal" if (art or cat == "framed art") else "unpriced",
        "confidence": round(statistics.mean(m["confidence"] for m in members), 2),
    })

json.dump(merged, open("items_merged.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("detections:", len(items), "-> unique objects:", len(merged))
for m in merged:
    print(" -", m["category"].ljust(12), "|", m["description"][:44].ljust(44), "|", f'{m["approx_width_cm"]}x{m["approx_height_cm"]}cm', "|", m["status"], "| merged", m["detections_merged"])
print("saved items_merged.json")
