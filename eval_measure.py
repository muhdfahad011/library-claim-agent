import csv, json, re

meas = json.load(open("measurements.json", encoding="utf-8"))

def toks(s):
    return set(w for w in re.sub(r"[^a-z0-9 ]", "", s.lower()).split() if len(w) > 1)

def sim(a, b):
    A, B = toks(a), toks(b)
    return len(A & B) / max(len(A), len(B)) if A and B else 0

rows = list(csv.DictReader(open("ground_truth_spines.csv", encoding="utf-8-sig")))
n = ok_h = ok_t = 0
print("title | height true/measured/err | thickness true/measured/err")
for r in rows:
    best = max(meas, key=lambda k: sim(r["title"], k), default=None)
    if not best or sim(r["title"], best) < 0.6:
        print(r["title"], "| no measurement")
        continue
    m = meas[best]
    th, tt = float(r["height_cm"]), float(r["thickness_cm"])
    eh = (m["spine_height_cm"] - th) / th * 100
    et = (m["spine_thickness_cm"] - tt) / tt * 100
    n += 1
    ok_h += abs(eh) <= 15
    ok_t += abs(et) <= 15
    print(f'{r["title"][:28].ljust(28)} | {th} / {m["spine_height_cm"]} / {eh:+.0f}% | {tt} / {m["spine_thickness_cm"]} / {et:+.0f}%')
print(f"\nwithin 15%: height {ok_h}/{n}, thickness {ok_t}/{n}  (pass bar: within 15% on a sample of 20)")
