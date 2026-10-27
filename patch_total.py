p = "finish_sweep.py"
s = open(p, encoding="utf-8").read()
old = 'total = sum(b["replacement_cost"]["amount"] for b in priced) if len(currencies) <= 1 else None'
new = 'total = sum(b["replacement_cost"]["amount"] for b in priced) if (priced and len(currencies) == 1) else None'
assert s.count(old) == 1, "anchor count %d" % s.count(old)
open(p, "w", encoding="utf-8").write(s.replace(old, new))
print("patched")
