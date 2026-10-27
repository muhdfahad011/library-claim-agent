import os, sys, json, time, statistics
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from PIL import Image

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"
FRAMES = sys.argv[1] if len(sys.argv) > 1 else "frames_books"
REF_KEY, REF_CM = "life 3", 19.05

class Box(BaseModel):
    title: str
    box_2d: list[int]

class Res(BaseModel):
    spines: list[Box]

PROMPT = (
    "For every book spine whose title is legible in this image, return the title and a tight bounding box box_2d as "
    "[ymin, xmin, ymax, xmax] normalized to 0-1000, covering the full visible spine from its top edge to its bottom edge. "
    "Do not guess titles."
)

found = json.load(open("spines_found.json", encoding="utf-8"))["books"]
ref = next((b for b in found if REF_KEY in b["title"].lower()), None)
if not ref:
    raise SystemExit("reference book not found in spines_found.json")
frames = sorted(set(ref["seen_in"]))
print("frames where the reference book is visible:", len(frames))

meas = {}
for f in frames:
    img = Image.open(os.path.join(FRAMES, f))
    W, H = img.size
    res, last = None, ""
    for _ in range(4):
        try:
            r = client.models.generate_content(model=MODEL, contents=[img, PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Res))
            res = r.parsed
            break
        except Exception as e:
            last = str(e)[:110]
            time.sleep(8)
    if res is None:
        print(f, "FAILED:", last)
        continue
    rb = next((s for s in res.spines if REF_KEY in s.title.lower() and len(s.box_2d) == 4), None)
    if not rb:
        print(f, "reference box not returned")
        continue
    ref_px = (rb.box_2d[2] - rb.box_2d[0]) / 1000 * H
    if ref_px < 20:
        print(f, "reference box too small")
        continue
    scale = REF_CM / ref_px
    for s in res.spines:
        if len(s.box_2d) != 4:
            continue
        hcm = (s.box_2d[2] - s.box_2d[0]) / 1000 * H * scale
        tcm = (s.box_2d[3] - s.box_2d[1]) / 1000 * W * scale
        meas.setdefault(s.title.strip().lower(), []).append((hcm, tcm))
    print(f, "| px per cm:", round(1 / scale, 1), "| spines boxed:", len(res.spines))
    time.sleep(1)

out = {}
print("\ntitle | height cm | thickness cm | frames used")
for t, v in meas.items():
    h = round(statistics.median(x[0] for x in v), 1)
    th = round(statistics.median(x[1] for x in v), 1)
    out[t] = {"spine_height_cm": h, "spine_thickness_cm": th, "frames": len(v)}
    print(t[:46].ljust(46), "|", h, "|", th, "|", len(v))
json.dump(out, open("measurements.json", "w", encoding="utf-8"), indent=2)
print("saved measurements.json")
