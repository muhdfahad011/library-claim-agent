p = "live_demo/server.py"
s = open(p, encoding="utf-8").read()
old = "                result = await _log_books(session, args)\n"
assert s.count(old) == 1, "anchor count %d" % s.count(old)
new = old + (
    "                with open('log_books_debug.txt', 'a', encoding='utf-8') as _f:\n"
    "                    _f.write(json.dumps(result, ensure_ascii=False, default=str) + chr(10))\n"
)
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("patched")
