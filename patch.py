p = open("price_all.py", encoding="utf-8").read()

def swap(old, new):
    global p
    assert old in p, "NOT FOUND: " + old[:50]
    p = p.replace(old, new)

swap("max_workers=2", "max_workers=1")

swap("""    data = r.json().get("data", {})
    rows = data.get("web", []) if isinstance(data, dict) else data
    urls = [x["url"] for x in rows if not any(s in x["url"] for s in SKIP)][:4]
    evidence = []
""", """    if r.status_code != 200:
        raise RuntimeError("search HTTP %s: %s" % (r.status_code, r.text[:120]))
    data = r.json().get("data", {})
    rows = data.get("web", []) if isinstance(data, dict) else data
    urls = [x["url"] for x in rows if not any(s in x["url"] for s in SKIP)][:4]
    if not urls:
        raise RuntimeError("search returned no usable URLs")
    time.sleep(2)
    evidence = []
""")

swap("""        try:
            s = requests.post("https://api.firecrawl.dev/v2/scrape", headers=FC, json={"url": u, "formats": ["markdown"]}, timeout=90)
            text = (s.json().get("data") or {}).get("markdown") or ""
        except Exception:
            text = ""
        ex = extract(text, title, author) if len(text) > 200 else None
        ok, why = verify(ex, text)
""", """        text, err = "", None
        try:
            s = requests.post("https://api.firecrawl.dev/v2/scrape", headers=FC, json={"url": u, "formats": ["markdown"]}, timeout=90)
            if s.status_code != 200:
                err = "scrape HTTP %s" % s.status_code
            text = (s.json().get("data") or {}).get("markdown") or ""
        except Exception as e:
            err = "scrape failed: " + str(e)[:60]
        time.sleep(1)
        ex = extract(text, title, author) if len(text) > 200 else None
        if err or (len(text) > 200 and ex is None):
            evidence.append({"url": u, "kind": "error: " + (err or "model call failed"), "retrieved_at": date.today().isoformat(), "extract": None})
            continue
        ok, why = verify(ex, text)
""")

swap("""    rep = [e for e in evidence if e["kind"] == "replacement"]""",
"""    if evidence and all(e["kind"].startswith("error") for e in evidence):
        raise RuntimeError("all pages errored: " + evidence[0]["kind"])
    rep = [e for e in evidence if e["kind"] == "replacement"]""")

swap("""    if key in done and "error" not in done[key]:
        return""", """    if key in done and "error" not in done[key] and done[key].get("replacement_cost"):
        return""")

open("price_all.py", "w", encoding="utf-8").write(p)
print("patched OK")
