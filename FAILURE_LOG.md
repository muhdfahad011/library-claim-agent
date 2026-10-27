# Failure log

## Three worst errors

**1. Failures hidden as "no price" (pricing).** Two parallel workers on free tiers hit rate limits, and my code recorded every failed call as "no verified price", so only 5 of 24 books were priced and it looked like the books could not be priced.
Root cause: errors were swallowed instead of recorded. Measured fix: run sequentially, record each failure with its reason, retry failed books. Result: 23 of 24 books priced from retrieved pages, each with URL and date. Not yet checked on a second set of books.

**2. Spine thickness fails the pass bar (measurement).** On a 480x854 WhatsApp video with one reference book (Life 3.0, 19.05 cm), height was within 15% on 3 of 3 hand-measured books (+13%, +12%, +2%), but thickness was within 15% on 0 of 3 (+62%, +116%, +84%). Boxes drawn by the model spilled onto the cover edge and gaps.
Root cause (not confirmed): a 1.9 cm spine is only about 37 px wide at that resolution, so a few extra pixels double it. Fix tried: crop each spine, enlarge 3x, re-box. Thickness only moved to +50%, +74%, +80%, still 0 of 3. A rule now blanks any size that was not measured in at least 2 frames or is physically implausible. Untested on original 1080p footage. Only 3 books were hand-measured, not 20.

**3. The agent claimed books were logged when the tool had failed (live agent).** The log_books tool failed on every call with "name 'types' is not defined" (a missing import in my patch), yet the agent said two books were successfully logged while the inventory showed 0.
Root cause: my code bug, plus an agent instruction that did not forbid confirming without a tool result. Fix: added the import and an instruction to report tool errors and never confirm a book the tool did not return. The inventory then showed the books. The instruction was not re-tested against a deliberate failure.

Other bugs found: a price median that mixed INR and USD (540 INR and 19.99 USD gave 279.995), fixed by tagging each source with its currency; an AbeBooks price accepted that matched no price on the page, fixed by never using marketplace pages for replacement cost; a stale server holding the port so the new tool was not loaded.

## Cost per sweep and latency per stage
Not measured. Known counts per sweep: about 11 to 21 Gemini Flash-Lite calls for spine reading (spines.py), 24 for other contents and spine boxes (stages.py), one per book for log_books during the live sweep. Firecrawl: pricing 24 books plus my experiments used up the free allowance, and credits per book were not logged. Latency per stage was not timed.

## What I would change with two more weeks
Film a real room in original 1080p with a flat A4 sheet as scale, measure 20 spines and 15 prices by hand, replace the model's boxes with a detector for spine edges, log credits and seconds per stage, and give the agent a tool-failure test.
