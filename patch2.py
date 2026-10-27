p = open("spines.py", encoding="utf-8").read()
a = 'MODEL = "gemini-3.5-flash"'
b = """        except Exception as e:
            time.sleep(8)"""
assert a in p and b in p, "pattern not found"
p = p.replace(a, 'MODEL = "gemini-3.5-flash-lite"')
p = p.replace(b, """        except Exception as e:
            last = str(e)[:110]
            time.sleep(8)""")
p = p.replace('print(f"[{k+1}/{len(frames)}] {f[\'file\']} FAILED")', 'print(f"[{k+1}/{len(frames)}] {f[\'file\']} FAILED: {last}")')
open("spines.py", "w", encoding="utf-8").write(p)
print("patched OK")
