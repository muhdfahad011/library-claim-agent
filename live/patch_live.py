def patch(path, edits):
    s = open(path, encoding="utf-8").read()
    for old, new in edits:
        n = s.count(old)
        assert n == 1, "anchor found %d times: %s" % (n, old[:70])
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)
    print("patched", path)

HELPER = r"""FRAME_MAX_AGE_SECONDS = 12.0

_SWEEPS = {}


def save_sweep_frame(session, data):
    key = id(session)
    if key not in _SWEEPS:
        d = APP_DIR / "sweeps" / datetime.now().strftime("%Y%m%d_%H%M%S")
        d.mkdir(parents=True, exist_ok=True)
        _SWEEPS[key] = {"dir": d, "t0": time.monotonic(), "frames": []}
    s = _SWEEPS[key]
    n = len(s["frames"])
    t = time.monotonic() - s["t0"]
    name = f"f_{n:04d}_{t:07.2f}s.jpg"
    (s["dir"] / name).write_bytes(data)
    s["frames"].append({"file": name, "t_s": round(t, 2), "sharpness": 0.0, "blurry": False})
    meta = {"video": "live sweep", "width": 0, "height": 0, "fps": 0, "frames": s["frames"]}
    (s["dir"] / "frames.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
"""

HIRES_BRANCH = r'''                        elif kind == "hires":
                            hdata = base64.b64decode(message.get("data") or "", validate=True)
                            if not hdata.startswith(b"\xff\xd8\xff") or len(hdata) > 4000000:
                                raise ValueError("Invalid high-resolution frame")
                            save_sweep_frame(session, hdata)
                        else:
                            encoded = message.get("data")'''

patch("live_demo/server.py", [
    ('"video": deque(), "camera_state": deque()}', '"video": deque(), "hires": deque(), "camera_state": deque()}'),
    ("FRAME_MAX_AGE_SECONDS = 12.0", HELPER.rstrip("\n")),
    ('                        else:\n                            encoded = message.get("data")', HIRES_BRANCH),
])

JS = r"""function sendHiRes() {
  if (!cameraStream || !liveSocket || liveSocket.readyState !== WebSocket.OPEN) return;
  if (!cameraPreview.videoWidth || liveSocket.bufferedAmount > 1500000) return;
  const w = Math.min(1920, cameraPreview.videoWidth);
  const h = Math.round(cameraPreview.videoHeight * w / cameraPreview.videoWidth);
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  c.getContext("2d").drawImage(cameraPreview, 0, 0, w, h);
  const dataUrl = c.toDataURL("image/jpeg", 0.9);
  liveSocket.send(JSON.stringify({ type: "hires", data: dataUrl.split(",")[1] }));
}

function sendFrame() {"""

patch("live_demo/app.js", [
    ("const FRAME_WIDTH = 512;", "const FRAME_WIDTH = 512;\nconst HIRES_INTERVAL_MS = 2000;\nlet hiresTimer = null;"),
    ("width: { ideal: 640 }, height: { ideal: 480 }", "width: { ideal: 1920 }, height: { ideal: 1080 }"),
    ("frameTimer = window.setInterval(sendFrame, FRAME_INTERVAL_MS);", "frameTimer = window.setInterval(sendFrame, FRAME_INTERVAL_MS);\n    hiresTimer = window.setInterval(sendHiRes, HIRES_INTERVAL_MS);"),
    ("if (frameTimer) window.clearInterval(frameTimer);", "if (frameTimer) window.clearInterval(frameTimer);\n  if (hiresTimer) window.clearInterval(hiresTimer);"),
    ("function sendFrame() {", JS),
])
