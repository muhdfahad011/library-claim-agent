import shutil
shutil.copy("stages.py", "stages.py.bak2")
s = open("stages.py", encoding="utf-8").read()
RULE = '''for b in out["books"]:
    ok = b["frames"] >= 2 and b["height_cm"] is not None and 12 <= b["height_cm"] <= 40 and 0.5 <= b["thickness_cm"] <= 0.6 * b["height_cm"]
    b["reliable"] = bool(ok)
    if not ok:
        b["thickness_cm"] = None
        if not b["is_reference"]:
            b["height_cm"] = None
'''
anchor = 'json.dump(out, open(os.path.join(base, "measurements.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)'
assert s.count(anchor) == 1, "anchor count %d" % s.count(anchor)
if 'b["reliable"]' not in s:
    s = s.replace(anchor, RULE + anchor)
open("stages.py", "w", encoding="utf-8").write(s)
print("patched stages.py")
