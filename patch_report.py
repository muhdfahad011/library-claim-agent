p = "make_report.py"
s = open(p, encoding="utf-8").read()
old1 = 'price, srcs, note = "not priced", "", ""'
new1 = 'price, srcs, note = "not retrieved", "", "Firecrawl credits exhausted, so no page could be searched"'
old2 = 'Marketplace and ebook prices are never used. {fx_line}'
new2 = 'Marketplace and ebook prices are never used. Where a price shows "not retrieved", the price lookup could not run because the Firecrawl credits were exhausted; no price was guessed. {fx_line}'
for o in (old1, old2):
    assert s.count(o) == 1, "anchor count %d: %s" % (s.count(o), o[:50])
s = s.replace(old1, new1).replace(old2, new2)
open(p, "w", encoding="utf-8").write(s)
print("patched")
