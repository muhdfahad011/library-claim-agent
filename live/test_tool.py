import os, glob, json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv(os.path.join("..", ".env"))

class S(BaseModel):
    title: str
    author: str | None
    confidence: float

class F(BaseModel):
    spines: list[S]
    unreadable_spines: int

latest = sorted(glob.glob("sweeps/*"))[-1]
frames = json.load(open(os.path.join(latest, "frames.json")))["frames"]
print("sweep:", latest, "| frames:", len(frames))
last = frames[-1]["file"]
data = open(os.path.join(latest, last), "rb").read()
print("last frame:", last, "| bytes:", len(data))
try:
    c = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    r = c.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=[types.Part.from_bytes(data=data, mime_type="image/jpeg"), "List every book whose title is legible on its spine or cover."],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=F))
    print("parsed:", r.parsed)
except Exception as e:
    print("ERROR:", type(e).__name__, str(e)[:300])
