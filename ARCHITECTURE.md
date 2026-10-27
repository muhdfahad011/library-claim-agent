# Architecture note

Phone or laptop browser -> live server (FastAPI, WebSocket) -> Gemini Live (voice, low-res video at 1 fps)
                                   |
                                   +-> sharp frames saved to live/sweeps/<time>/ (frame_ref for every item)
                                   +-> log_books tool -> Gemini 3.5 Flash-Lite reads spines -> live inventory box + inventory.json

After the sweep (background stages, each a separate script with its own output file):
  stages.py       -> items.json (other contents), measurements.json (spine sizes)
  price_all.py    -> prices.json (Firecrawl pages + Gemini quote extraction + code verification)
  reprice.py      -> prices_final.json (currency tagging, local price preferred, dated FX conversion)
  finish_sweep.py -> claim_packet.json + report.html (totals computed in code, review queue)

Which model does what: Gemini Live talks and sees; Gemini 3.5 Flash-Lite reads text and draws boxes; Firecrawl retrieves web pages; code verifies prices and computes every total.

Metric scale: a reference book of known height (reference.json, currently Life 3.0 at 19.05 cm) found in each sampled frame gives centimetres per pixel; assumes the other books are in the same plane. Thickness is unreliable at low resolution. No LiDAR or depth is used.

Prices: only from retrieved retailer pages, each with URL, retrieval date and the quoted sentence; marketplace and ebook prices are never used for replacement cost; unknowns stay empty and go to the review queue.
