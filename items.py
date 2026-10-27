import os, sys, json, re, time
from difflib import SequenceMatcher
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from PIL import Image

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"
FRAMES = sys.argv[1] if len(sys.argv) > 1 else "frames"
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 6

class Item(BaseModel):
    category: str
    description: str
    material: str | None
    approx_width_cm: float | None
    approx_height_cm: float | None
    brand_model: str | None
    is_art_or_portrait: bool
    confidence: float

class Result(BaseModel):
    items: list[Item]

PROMPT = (
    "This is one frame from a video of a room. List every object that is NOT a book: furniture, shelving, lamps, electronics, "
    "appliances, rugs, decor, framed art and portraits. For each give a category, a short description, the main material if visible, "
    "approximate width and height in centimetres (null if you cannot judge), brand or model ONLY if legible in the image (else null), "
    "whether it is art or a portrait, and confidence 0 to 1. Do not invent brands or models."
)

def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()

meta = json.load(open(os.path.join(FRAMES, "frames.json"), encoding="utf-8"))
frames = meta["frames"][::STEP]
print("frames to read:", len(frames))
items, errors = [], 0
for k, f in enumerate(frames):
    img = Image.open(os.path.join(FRAMES, f["file"]))
    res, last = None, ""
    for _ in range(4):
        try:
            r = client.models.generate_content(model=MODEL, contents=[img, PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Result))
            res = r.parsed
            break
        except Exception as e:
            last = str(e)[:110]
            time.sleep(8)
    if res is None:
        errors += 1
        print(f"[{k+1}/{len(frames)}] FAILED: {last}")
        continue
    for it in res.items:
        hit = next((x for x in items if x["category"].lower() == it.category.lower()
                    and SequenceMatcher(None, norm(x["description"]), norm(it.description)).ratio() > 0.75), None)
        if hit:
            hit["seen_in"].append(f["file"])
        else:
            d = it.model_dump()
            d["frame_ref"] = f["file"]
            d["seen_in"] = [f["file"]]
            d["status"] = "needs_appraisal" if it.is_art_or_portrait else "unpriced"
            items.append(d)
    print(f"[{k+1}/{len(frames)}] items this frame: {len(res.items)} | unique so far: {len(items)}", flush=True)
    time.sleep(1)

json.dump(items, open("items_found.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\nUNIQUE ITEMS:", len(items), "| frames failed:", errors)
for x in items:
    print(" -", x["category"], "|", x["description"][:50], "|", x["brand_model"], "|", x["status"])
print("saved items_found.json")
