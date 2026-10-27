import sys, os, json
import cv2

path = sys.argv[1]
out_dir = sys.argv[2] if len(sys.argv) > 2 else "frames"
every_s, max_frames = 0.5, 300
os.makedirs(out_dir, exist_ok=True)

cap = cv2.VideoCapture(path)
if not cap.isOpened():
    sys.exit("cannot open video: " + path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"video {w}x{h} | {fps:.1f} fps | {total/fps:.1f} s")

step = max(1, int(round(fps * every_s)))
manifest, i = [], 0
while len(manifest) < max_frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, frame = cap.read()
    if not ok:
        break
    sharp = cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
    t = i / fps
    name = f"f_{len(manifest):04d}_{t:07.2f}s.jpg"
    cv2.imwrite(os.path.join(out_dir, name), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    manifest.append({"file": name, "t_s": round(t, 2), "sharpness": float(round(sharp, 1))})
    i += step

sh = sorted(m["sharpness"] for m in manifest)
med = sh[len(sh) // 2] if sh else 0
for m in manifest:
    m["blurry"] = bool(m["sharpness"] < 0.5 * med)
json.dump({"video": path, "width": w, "height": h, "fps": fps, "frames": manifest},
          open(os.path.join(out_dir, "frames.json"), "w", encoding="utf-8"), indent=2)
print(f"saved {len(manifest)} frames to {out_dir}/ | blurry: {sum(m['blurry'] for m in manifest)}")
