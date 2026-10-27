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
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 3

class Spine(BaseModel):
    title: str
    author: str | None
    row: str
    horizontal: str
    confidence: float

class FrameResult(BaseModel):
    spines: list[Spine]
    unreadable_spines: int

PROMPT = (
    "This is one frame from a video of bookshelves. List every book whose spine or cover title is clearly legible. "
    "For each give the title, the author if readable (else null), which shelf row it is on (for example top, upper-middle, lower), "
    "its horizontal position (left, center or right of the frame), and your confidence from 0 to 1. "
    "Do not guess any title you cannot read. Also give unreadable_spines: how many book spines are visible but too small, blurry, "
    "cut off or angled to read."
)

def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()

def same(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b or (len(a) > 8 and len(b) > 8 and (a in b or b in a)):
        return True
    return SequenceMatcher(None, a, b).ratio() > 0.88

meta = json.load(open(os.path.join(FRAMES, "frames.json"), encoding="utf-8"))
frames = meta["frames"][::STEP]
print("frames to read:", len(frames))

books, per_frame, errors = [], [], 0
for k, f in enumerate(frames):
    img = Image.open(os.path.join(FRAMES, f["file"]))
    res = None
    for attempt in range(4):
        try:
            r = client.models.generate_content(model=MODEL, contents=[img, PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=FrameResult))
            res = r.parsed
            break
        except Exception as e:
            last = str(e)[:110]
            time.sleep(8)
    if res is None:
        errors += 1
        print(f"[{k+1}/{len(frames)}] {f['file']} FAILED: {last}")
        continue
    new = 0
    for s in res.spines:
        hit = next((b for b in books if same(b["title"], s.title)), None)
        if hit:
            hit["seen_in"].append(f["file"])
            if s.confidence > hit["confidence"]:
                hit["confidence"] = s.confidence
            if not hit["author"] and s.author:
                hit["author"] = s.author
        else:
            new += 1
            books.append({"title": s.title, "author": s.author, "confidence": s.confidence,
                          "frame_ref": f["file"], "t_s": f["t_s"], "row": s.row, "horizontal": s.horizontal,
                          "seen_in": [f["file"]]})
    per_frame.append({"frame": f["file"], "legible": len(res.spines), "unreadable": res.unreadable_spines})
    print(f"[{k+1}/{len(frames)}] {f['file']} legible: {len(res.spines)} | unreadable: {res.unreadable_spines} | new books: {new} | total so far: {len(books)}", flush=True)
    time.sleep(1)

json.dump({"books": books, "per_frame": per_frame}, open("spines_found.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\nUNIQUE BOOKS FOUND:", len(books), "| frames failed:", errors)
print("most unreadable spines in one frame:", max([p["unreadable"] for p in per_frame] or [0]))
print("\nfirst 15 titles:")
for b in books[:15]:
    print(" ", b["title"][:60], "|", b["author"], "|", b["confidence"], "|", b["frame_ref"])
print("saved spines_found.json")
