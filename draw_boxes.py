import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from PIL import Image, ImageDraw

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class Box(BaseModel):
    title: str
    box_2d: list[int]

class Res(BaseModel):
    spines: list[Box]

img = Image.open("frames_books/f_0008_0004.02s.jpg").convert("RGB")
W, H = img.size
print("frame size:", W, "x", H)
r = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=[img, "For every book spine whose title is legible, return the title and a tight bounding box box_2d as [ymin, xmin, ymax, xmax] normalized to 0-1000, covering the full visible spine from its top edge to its bottom edge."],
    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Res))
d = ImageDraw.Draw(img)
for s in r.parsed.spines:
    y0, x0, y1, x1 = s.box_2d
    px0, py0, px1, py1 = x0 / 1000 * W, y0 / 1000 * H, x1 / 1000 * W, y1 / 1000 * H
    d.rectangle([px0, py0, px1, py1], outline=(255, 0, 0), width=2)
    print(s.title[:30].ljust(30), "| box px: width", round(px1 - px0), "height", round(py1 - py0))
img.save("boxes_check.jpg")
print("saved boxes_check.jpg")
