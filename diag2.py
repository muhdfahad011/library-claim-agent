import os
from dotenv import load_dotenv
from google import genai
from PIL import Image
load_dotenv()
c = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
img = Image.open("frames/f_0021_0010.50s.jpg")
print("image size:", img.size)
for m in ("gemini-3.5-flash", "gemini-3.5-flash-lite"):
    try:
        r = c.models.generate_content(model=m, contents=[img, "How many book spines are visible? One number only."])
        print(m, "->", r.text.strip()[:60])
    except Exception as e:
        print(m, "ERROR:", type(e).__name__, str(e)[:250])
