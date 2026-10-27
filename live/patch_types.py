import shutil
for f in ("server.py", "live_tools.py"):
    shutil.copy("live_demo/" + f, "live_demo/" + f + ".bak3")

def patch(path, old, new):
    s = open(path, encoding="utf-8").read()
    n = s.count(old)
    assert n == 1, "anchor found %d times: %s" % (n, old[:60])
    open(path, "w", encoding="utf-8").write(s.replace(old, new))
    print("patched", path)

patch("live_demo/server.py",
      "async def _log_books(session, args):\n",
      "async def _log_books(session, args):\n    from google.genai import types\n")

patch("live_demo/live_tools.py",
      "Do not give prices or measurements; ",
      "If log_books returns an error, tell the user plainly that logging failed and that you will retry; "
      "never say a book was logged unless the tool result lists it in added or the total went up. "
      "Do not give prices or measurements; ")
