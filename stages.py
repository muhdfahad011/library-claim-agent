import os, sys, json, glob, re, time, statistics
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from PIL import Image

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"
N = 12

base = sys.argv[1] if len(sys.argv) > 1 else None
if base is None:
    cands = [d for d in sorted(glob.glob("live/sweeps/*")) if os.path.exists(os.path.join(d, "inventory.json"))]
    if not cands:
        raise SystemExit("no sweep folder with inventory.json found under live/sweeps")
    base = cands[-1]
frames = json.load(open(os.path.join(base, "frames.json"), encoding="utf-8"))["frames"]
idx = sorted(set(int(i * len(frames) / N) for i in range(N)))
pick = [frames[i] for i in idx]
sweep_name = os.path.basename(base)
print("sweep:", base, "| frames:", len(frames), "| sampled:", len(pick))


def call(img, prompt, schema):
    last = ""
    for _ in range(4):
        try:
            r = client.models.generate_content(model=MODEL, contents=[img, prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema))
            return r.parsed, ""
        except Exception as e:
            last = str(e)[:100]
            time.sleep(6)
    return None, last


class Item(BaseModel):
    category: str
    description: str
    brand_model: str | None
    is_art: bool
    confidence: float


class ItemList(BaseModel):
    new_items: list[Item]


items, item_fail = [], 0
for f in pick:
    img = Image.open(os.path.join(base, f["file"])).convert("RGB")
    known = "\n".join("- [%s] %s" % (x["category"], x["description"]) for x in items) or "(none yet)"
    prompt = (
        "This is one frame from a live camera sweep of a room. Objects already listed:\n" + known + "\n\n"
        "List only objects that are NOT books, NOT people and NOT already listed. The same physical object seen from another angle "
        "or partly visible counts as already listed. For each give: category (one of shelving, furniture, framed art, decor, electronics, "
        "lighting, rug, appliance, other), a short description, brand or model ONLY if legible in the image (else null), is_art true for "
        "framed art, paintings, posters or portraits, and confidence 0 to 1. Do not invent brands. Return an empty list if nothing is new."
    )
    res, err = call(img, prompt, ItemList)
    if res is None:
        item_fail += 1
        print(f["file"], "items FAILED:", err)
        continue
    for it in res.new_items:
        d = it.model_dump()
        d["category"] = d["category"].strip().lower()
        d["frame_ref"] = sweep_name + "/" + f["file"]
        items.append(d)
    print(f["file"], "| new items:", len(res.new_items), "| total:", len(items))
json.dump(items, open(os.path.join(base, "items.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("ITEMS:", len(items), "| frames failed:", item_fail)


class Box(BaseModel):
    title: str
    box_2d: list[int]


class Boxes(BaseModel):
    spines: list[Box]


def toks(s):
    return set(w for w in re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).split() if len(w) > 1)


def same(a, b):
    x, y = toks(a), toks(b)
    return bool(x and y) and len(x & y) / max(len(x), len(y)) >= 0.6


if not os.path.exists("reference.json"):
    raise SystemExit("no reference.json: spine sizes skipped")
ref = json.load(open("reference.json", encoding="utf-8-sig"))
PB = ("For every book spine whose title is legible, return the title and a tight bounding box box_2d as [ymin, xmin, ymax, xmax] "
      "normalized to 0-1000, covering the full visible spine from its top edge to its bottom edge.")
groups, ref_title, used, spine_fail = [], None, 0, 0
for f in pick:
    img = Image.open(os.path.join(base, f["file"])).convert("RGB")
    W, H = img.size
    res, err = call(img, PB, Boxes)
    if res is None:
        spine_fail += 1
        print(f["file"], "spines FAILED:", err)
        continue
    rb = next((s for s in res.spines if ref["title_contains"].lower() in s.title.lower() and len(s.box_2d) == 4), None)
    if not rb or rb.box_2d[2] <= rb.box_2d[0]:
        print(f["file"], "| reference book not found")
        continue
    ref_px = (rb.box_2d[2] - rb.box_2d[0]) / 1000 * H
    if ref_px < 30:
        print(f["file"], "| reference box too small")
        continue
    ref_title = ref_title or rb.title
    cm_per_px = ref["height_cm"] / ref_px
    used += 1
    for s in res.spines:
        if len(s.box_2d) != 4 or s.box_2d[2] <= s.box_2d[0] or s.box_2d[3] <= s.box_2d[1]:
            continue
        h = (s.box_2d[2] - s.box_2d[0]) / 1000 * H * cm_per_px
        t = (s.box_2d[3] - s.box_2d[1]) / 1000 * W * cm_per_px
        g = next((g for g in groups if same(g["title"], s.title)), None)
        if g is None:
            g = {"title": s.title, "h": [], "t": []}
            groups.append(g)
        g["h"].append(h)
        g["t"].append(t)
    print(f["file"], "| reference found | cm per px:", round(cm_per_px, 4))

out = {"reference": {"title": ref_title or ref["title_contains"], "height_cm": ref["height_cm"]},
       "frames_used": used, "frames_sampled": len(pick), "books": []}
for g in groups:
    out["books"].append({"title": g["title"], "height_cm": round(statistics.median(g["h"]), 1),
                         "thickness_cm": round(statistics.median(g["t"]), 1), "frames": len(g["h"]),
                         "is_reference": ref["title_contains"].lower() in g["title"].lower()})
for b in out["books"]:
    ok = b["frames"] >= 2 and b["height_cm"] is not None and 12 <= b["height_cm"] <= 40 and 0.5 <= b["thickness_cm"] <= 0.6 * b["height_cm"]
    b["reliable"] = bool(ok)
    if not ok:
        b["thickness_cm"] = None
        if not b["is_reference"]:
            b["height_cm"] = None
json.dump(out, open(os.path.join(base, "measurements.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\nSPINES MEASURED:", len(out["books"]), "| frames with the reference visible:", used, "of", len(pick))
for b in out["books"]:
    print(" ", b["title"][:40].ljust(40), "| h:", b["height_cm"], "| t:", b["thickness_cm"], "| frames:", b["frames"])
