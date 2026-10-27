# Failure log (draft, edit in your own words)

1. **Google Books price lookup failed.** Anonymous requests returned 429 (daily quota). With my Gemini key it returned 401. Even when it works it mostly gives ebook prices, which are not valid replacement costs for printed books. Dropped it.
2. **Model-guessed prices rejected.** My first pricing script asked Gemini for typical prices from memory. The brief forbids prices without a retrievable source. Replaced with: Firecrawl retrieves retailer pages, Gemini extracts only from the page text and quotes the exact sentence, and code checks the quote is really on the page.
3. **Gemini Google Search grounding returned 429** on a free-tier key, so it could not be the price source.
4. **Model availability.** gemini-2.5-flash returned 404 (no longer available to new users). Newer Flash models intermittently returned 503 (high demand). Switched models and retried.
5. **Open Library identification is only partly reliable.** Publisher fields were often from another edition (an audiobook publisher, a children's imprint). The ISBN for *1491* was the ebook's ISBN. Two matches were wrong (Cuba: An American History; How Europe Underdeveloped Africa) and were caught by a validation step. The packet now keeps `isbn` empty and stores the unconfirmed one as `isbn_candidate`.
6. **Retailer pages.** Amazon returned a generic page with no price. An AbeBooks price of $18.63 was accepted although the page showed only used $14.98 and new $56.68. Marketplace pages are now never used for replacement cost.
7. **Currency bug.** The median mixed INR and USD (540 INR with 19.99 USD became 279.995) and treated GBP as USD. Fixed by tagging every source with its currency, using local INR prices when they exist, and otherwise converting with a dated exchange rate (frankfurter).
8. **Rate limits hidden as "no price".** Two parallel workers on free tiers made failed calls look like missing prices (5 of 24 priced). Now sequential, errors are recorded as errors, and failed books are retried (23 of 24 priced).
9. **Same page, different prices.** One publisher page gave $16.80 on one run and $21.00 on another (list vs discounted price). Now both fields are extracted and the payable price is used.
10. **Reference app limits.** It sends 512 px frames at 1 fps and keeps only the latest frame, which cannot read shelf spines or give a saved frame per item. Planned: separate high-resolution capture saved to disk.
11. **File named inspect.py** shadowed Python's own module and crashed an unrelated script. Renamed.

## Still open
- 15 prices need hand-checking against the real product pages.
- Country and currency should come from the conversation, not a default.
- Video sweep, spine measurement, room area, non-book items, ground truth.

## Measurement results (3-book test, 480 x 854 WhatsApp video)
- Scale came from one reference book (Life 3.0, 19.05 cm, same-plane assumption). Pixels per cm stayed stable at about 19.4 to 19.8 across frames.
- Height: 3 of 3 within 15% of tape (+13%, +12%, +2%), all leaning high.
- Thickness: 0 of 3 within 15% (+62%, +116%, +84%). Fails the pass bar.
- Boxes drawn by the model spilled onto the cover edge and gaps (seen in boxes_check.jpg). Books were at the same distance as the reference, so distance error is not the cause here.
- Fix tried: crop each spine, enlarge 3x, re-box the spine face only. Thickness errors only moved to +50%, +74%, +80%. Still 0 of 3.
- Probable cause (not confirmed): a 1.9 cm spine is only about 37 px wide at this resolution, so a few extra pixels per edge doubles the value. Untested on original-quality 1080p footage.
- Limits of this test: 3 books, not the required 20; tape readings were to the nearest quarter inch (about 0.6 cm), which alone is about 17% on a 1.9 cm spine. Final run should use a ruler in millimetres.
- Not done: no correction factor was applied, because tuning to 3 books would only fit this table.

## Live agent failures found while testing
- The log_books tool failed on every call with "name 'types' is not defined" (my patch used a library name the file never imported). It failed in 1 to 28 ms, before reaching the model.
- While the tool was failing, the agent told me two books had been "successfully logged" when the inventory showed zero. Fix: the agent is now told to say so when the tool errors and never to confirm a book the tool did not return. Not yet re-tested against a deliberate failure.
- An old server kept the port, so my first tests ran the old code without the new tool. Found from a port-in-use error.
- Firecrawl free credits ran out (0 left), so prices cannot be retrieved. The report states this where prices would appear.
