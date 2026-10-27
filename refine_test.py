import os, csv, json, re, statistics, time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from PIL import Image

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"
FR = ["f_0004_0002.01s.jpg", "f_0006_0003.01s.jpg", "f_0008_0004.02s.jpg", "f_0012_0006.02s.jpg", "f_0014_0007.03s.jpg"]
REF_KEY, REF_CM, UP = "life 3", 19.05, 3

class Box(BaseModel):
    title: str
    box_2d: list[int]

class Res(BaseModel):
    spines: list[Box]

class One(BaseModel):
    box_2d: list[int]

P1 = ("For every book spine whose title is legible, return the title and a tight bounding box box_2d as "
      "[ymin, xmin, ymax, xmax] normalized to 0-1000, covering the full visible spine from its top edge to its bottom edge.")
P2 = ("This enlarged crop shows one book spine in the middle, with parts of neighbouring books at the sides. Return box_2d as "
      "[ymin, xmin, ymax, xmax] normalized to 0-1000 for ONLY the narrow spine face that carries the title. Exclude the front cover edge, "
      "any gap between books, and neighbouring books. The box edges must sit exactly on the left and right edges of the spine.")

def call(img, prompt, schema):
    for _ in range(4):
        try:
            r = client.models.generate_content(model=MODEL, contents=[img, prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema))
            return r.parsed
        except Exception:
            time.sleep(6)
    return None

A, B = {}, {}
for f in FR:
    img = Image.open(os.path.join("frames_books", f)).convert("RGB")
    W, H = img.size
    res = call(img, P1, Res)
    if not res:
        print(f, "pass 1 failed")
        continue
    ref = next((s for s in res.spines if REF_KEY in s.title.lower() and len(s.box_2d) == 4), None)
    if not ref:
        print(f, "no reference box")
        continue
    scale = REF_CM / ((ref.box_2d[2] - ref.box_2d[0]) / 1000 * H)
    for s in res.spines:
        if len(s.box_2d) != 4:
            continue
        y0, x0, y1, x1 = s.box_2d
        px0, py0, px1, py1 = x0 / 1000 * W, y0 / 1000 * H, x1 / 1000 * W, y1 / 1000 * H
        key = s.title.strip().lower()
        A.setdefault(key, []).append((px1 - px0) * scale)
        mx = 0.6 * (px1 - px0)
        cx0, cx1 = max(0, px0 - mx), min(W, px1 + mx)
        crop = img.crop((int(cx0), int(py0), int(cx1), int(py1)))
        cw, ch = crop.size
        if cw < 8 or ch < 8:
            continue
        crop = crop.resize((cw * UP, ch * UP), Image.LANCZOS)
        one = call(crop, P2, One)
        if one and len(one.box_2d) == 4:
            wpx = (one.box_2d[3] - one.box_2d[1]) / 1000 * cw
            B.setdefault(key, []).append(wpx * scale)
    print(f, "| cm per px:", round(scale, 4))

def toks(s):
    return set(w for w in re.sub(r"[^a-z0-9 ]", "", s.lower()).split() if len(w) > 1)

def sim(a, b):
    x, y = toks(a), toks(b)
    return len(x & y) / max(len(x), len(y)) if x and y else 0

rows = list(csv.DictReader(open("ground_truth_spines.csv", encoding="utf-8-sig")))
print("\nbook | true | A (old) | B (refined)")
okA = okB = n = 0
for r in rows:
    tt = float(r["thickness_cm"])
    ka = max(A, key=lambda k: sim(r["title"], k), default=None)
    if not ka or sim(r["title"], ka) < 0.6 or ka not in B:
        print(r["title"], "| no data")
        continue
    a, b = statistics.median(A[ka]), statistics.median(B[ka])
    n += 1
    okA += abs(a - tt) / tt <= 0.15
    okB += abs(b - tt) / tt <= 0.15
    print(f'{r["title"][:26].ljust(26)} | {tt} | {a:.1f} ({(a-tt)/tt*100:+.0f}%) | {b:.1f} ({(b-tt)/tt*100:+.0f}%)')
print(f"\nthickness within 15%: old {okA}/{n}, refined {okB}/{n}")
