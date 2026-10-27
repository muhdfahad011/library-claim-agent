import shutil

for f in ("server.py", "app.js", "live_tools.py"):
    shutil.copy("live_demo/" + f, "live_demo/" + f + ".bak2")

def patch(path, edits):
    s = open(path, encoding="utf-8").read()
    for old, new in edits:
        n = s.count(old)
        assert n == 1, "anchor found %d times: %s" % (n, old[:70])
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)
    print("patched", path)

SERVER_BLOCK = r'''_SW_SPINE_MODEL = "gemini-3.5-flash-lite"
_SW_INVENTORY = {}
_SW_PROMPT = (
    "This is one frame from a live camera sweep of bookshelves. List every book whose spine or cover title is clearly legible, "
    "with the title, the author if readable (else null) and your confidence from 0 to 1. Do not guess any title you cannot read. "
    "Also give unreadable_spines: how many book spines are visible but too small, blurry, cut off or angled to read."
)


class _SwSpine(BaseModel):
    title: str
    author: str | None
    confidence: float


class _SwFrame(BaseModel):
    spines: list[_SwSpine]
    unreadable_spines: int


def _sw_norm(s):
    import re
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def _sw_same(a, b):
    from difflib import SequenceMatcher
    a, b = _sw_norm(a), _sw_norm(b)
    if not a or not b:
        return False
    if a == b or (len(a) > 8 and len(b) > 8 and (a in b or b in a)):
        return True
    return SequenceMatcher(None, a, b).ratio() > 0.88


def _inventory_view(session):
    return [{"title": b["title"], "author": b["author"], "confidence": b["id_confidence"]}
            for b in _SW_INVENTORY.get(id(session), [])]


async def _log_books(session, args):
    sw = _SWEEPS.get(id(session))
    if not sw or not sw["frames"]:
        return {"error": "No sharp camera frame has arrived yet. Ask the user to turn the camera on and hold still."}
    last = sw["frames"][-1]
    if time.monotonic() - sw["t0"] - last["t_s"] > 15:
        return {"error": "The latest camera frame is stale. Ask the user to check that the camera is on."}
    data = (sw["dir"] / last["file"]).read_bytes()
    try:
        client = _client()

        def work():
            return client.models.generate_content(
                model=_SW_SPINE_MODEL,
                contents=[types.Part.from_bytes(data=data, mime_type="image/jpeg"), _SW_PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=_SwFrame),
            )

        r = await asyncio.wait_for(asyncio.to_thread(work), 40)
        res = r.parsed
    except Exception as exc:
        return {"error": "Book reading failed: " + str(exc)[:80]}
    if res is None:
        return {"error": "Book reading returned nothing. Ask the user to hold the books steady and try again."}
    inv = _SW_INVENTORY.setdefault(id(session), [])
    added = []
    for s in res.spines:
        hit = next((b for b in inv if _sw_same(b["title"], s.title)), None)
        if hit:
            if s.confidence > hit["id_confidence"]:
                hit["id_confidence"] = s.confidence
            continue
        inv.append({"id": "book-%03d" % (len(inv) + 1), "title": s.title, "author": s.author or "",
                    "id_confidence": s.confidence, "status": "identified",
                    "frame_ref": sw["dir"].name + "/" + last["file"]})
        added.append(s.title)
    (sw["dir"] / "inventory.json").write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
    if not res.spines:
        advice = "No legible spines in this frame. Ask the user to move closer, slow down and turn the spines toward the camera."
    elif res.unreadable_spines:
        advice = "Some spines were unreadable. Ask the user to slow down, step closer or add light for those."
    else:
        advice = "All visible spines were readable. Ask the user to continue to the next shelf."
    return {"added": added, "total_books": len(inv), "legible_in_frame": len(res.spines),
            "unreadable_in_frame": res.unreadable_spines, "advice": advice}


async def _draw_incident_sketch(session: IntakeSession, args: dict[str, Any]) -> dict[str, Any]:'''

patch("live_demo/server.py", [
    ("async def _draw_incident_sketch(session: IntakeSession, args: dict[str, Any]) -> dict[str, Any]:", SERVER_BLOCK),
    ('            elif name == "draw_incident_sketch":\n                result = await _draw_incident_sketch(session, args)\n',
     '            elif name == "draw_incident_sketch":\n                result = await _draw_incident_sketch(session, args)\n'
     '            elif name == "log_books":\n                result = await _log_books(session, args)\n'
     '                await send({"type": "inventory", "books": _inventory_view(session)})\n'),
])

JS_BLOCK = r'''function renderInventory(books) {
  let box = document.getElementById("sweepInventory");
  if (!box) {
    box = document.createElement("div");
    box.id = "sweepInventory";
    box.style.cssText = "position:fixed;right:12px;bottom:12px;width:300px;max-height:45vh;overflow:auto;z-index:50;padding:10px 12px;border:1px solid GrayText;border-radius:8px;background:Canvas;color:CanvasText;font:13px/1.4 system-ui,sans-serif";
    document.body.appendChild(box);
  }
  box.textContent = "";
  const h = document.createElement("strong");
  h.textContent = "Inventory: " + books.length + " books";
  box.appendChild(h);
  const ol = document.createElement("ol");
  ol.style.cssText = "margin:6px 0 0;padding-left:20px";
  for (const b of books) {
    const li = document.createElement("li");
    li.textContent = b.title + (b.author ? " (" + b.author + ")" : "");
    ol.appendChild(li);
  }
  box.appendChild(ol);
}

function sendHiRes() {'''

patch("live_demo/app.js", [
    ("function sendHiRes() {", JS_BLOCK),
    ('} else if (message.type === "interrupted") {',
     '} else if (message.type === "inventory") {\n        renderInventory(message.books);\n      } else if (message.type === "interrupted") {'),
])

DECL = r'''    log_books = types.FunctionDeclaration(
        name="log_books",
        description=(
            "Read the book spines in the newest sharp camera frame and add any new books to the live inventory. "
            "Runs in the background. Returns the titles added, the running total, how many spines were unreadable, "
            "and advice on what to ask the user to do next."
        ),
        behavior=types.Behavior.NON_BLOCKING,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "reason": _string_param("One short phrase on why you are reading the shelf now, for example new shelf in view."),
            },
        ),
    )
    return [types.Tool(function_declarations=[lookup, sync, pin_photo, sketch, log_books])]'''

SWEEP = r'''SWEEP_INSTRUCTION = (
    "LIBRARY SWEEP MODE. In this session you inventory a home library for a contents claim. You are not taking an accident claim, "
    "so do not ask for a policy number or incident details. Greet the user, confirm their country and currency, and explain in one or two "
    "sentences that they should pan slowly across the shelves with the spines facing the camera. Whenever books are in view, call log_books "
    "(not more than once every few seconds, and again after the view changes) and use it instead of pin_evidence_photo for books. "
    "Only say book titles that log_books returned; never name a title from your own reading or memory. If log_books reports unreadable "
    "spines or none legible, ask the user to slow down, step closer, tilt the camera or add light. Do not give prices or measurements; "
    "those are worked out after the sweep. Tell the user briefly what you just logged."
)


def build_live_config(
    *,'''

patch("live_demo/live_tools.py", [
    ("    return [types.Tool(function_declarations=[lookup, sync, pin_photo, sketch])]", DECL),
    ("def build_live_config(\n    *,", SWEEP),
    ("            SYSTEM_INSTRUCTION,\n            camera_mode_instruction(camera_enabled),",
     "            SYSTEM_INSTRUCTION,\n            SWEEP_INSTRUCTION,\n            camera_mode_instruction(camera_enabled),"),
])

WRAP = r'''


_orig_tool_headline = tool_headline


def tool_headline(name, args, result):
    if name == "log_books":
        if result is None:
            return "Reading the books in view"
        if isinstance(result, dict) and result.get("error"):
            return str(result["error"])
        return "Logged %d new books (total %s)" % (len(result.get("added", [])), result.get("total_books"))
    return _orig_tool_headline(name, args, result)
'''
s = open("live_demo/live_tools.py", encoding="utf-8").read()
open("live_demo/live_tools.py", "w", encoding="utf-8").write(s.rstrip("\n") + WRAP)
print("added tool_headline wrapper")
