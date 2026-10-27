import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from PIL import Image

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.8-flash"


class Book(BaseModel):
    title: str
    author: str | None
    confidence: float  # 0.0 to 1.0


img = Image.open("shelf.png")

resp = client.models.generate_content(
    model=MODEL,
    contents=[
        img,
        "List every book spine visible in this image. For each, give the "
        "title, the author if readable (otherwise null), and your confidence "
        "from 0 to 1. Do not guess titles you cannot read.",
    ],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=list[Book],
    ),
)

print(resp.text)
open("books.json","w",encoding="utf-8").write(resp.text)
