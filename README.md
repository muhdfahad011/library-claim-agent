# Library Contents Claim Agent (partial submission)

A live voice-and-camera agent that logs the books in a home library during a sweep, then builds a claim packet and report. This submission is **incomplete**: see "What is not done".

## Run it (about 15 minutes)
1. Python 3.12 or 3.13. Create a venv for the tools and install: `pip install google-genai python-dotenv pillow opencv-python pydantic requests openpyxl`
2. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` (Google AI Studio) and `FIRECRAWL_API_KEY`.
3. Live app: in `live/`, create a second venv, `pip install -r requirements.txt`, create `live/.env` with `GOOGLE_GENAI_USE_VERTEXAI=False` and `GOOGLE_API_KEY=...`, then run `python -m uvicorn live_demo.server:app --host 127.0.0.1 --port 4177` and open http://127.0.0.1:4177. Use headphones.
4. Turn on camera and microphone, show books spines-forward, and say "please log these books". Frames are saved under `live/sweeps/<time>/`.
5. After the sweep, from the project root: `python stages.py` (other contents and spine sizes), then `python finish_sweep.py` (packet and report written into the sweep folder).

## What was kept, changed and thrown away from the reference app
- **Kept:** the Gemini Live voice session, browser microphone and camera, tool-calling pattern, notebook and transcript UI.
- **Changed:** the browser also sends a sharp 1920-wide frame every 2 s (the reference sends 512 px at 1 fps and keeps only the latest). The server saves every sharp frame with a timestamp, so each item has a `frame_ref`. Added a `log_books` tool, an on-screen inventory box and a sweep-mode instruction.
- **Thrown away (not removed from the code yet):** the insurance policy lookup, claim workflow and sketch tools. The "claim update failed" message in the UI comes from that old workflow.

## Pipeline
1. Sharp frames saved during the live sweep (or extracted from a video with `extract_frames.py`).
2. `log_books` (live) or `spines.py` (offline): Gemini 3.5 Flash-Lite reads legible spines; titles are merged by fuzzy match; unreadable spines are counted, never guessed.
3. `stages.py`: other contents by Gemini (art flagged needs_appraisal, sizes left empty); spine boxes by Gemini converted to cm using a reference book of known height (`reference.json`).
4. Pricing (`price_all.py`, `reprice.py`): Firecrawl retrieves retailer pages; Gemini reads a price and must quote the exact sentence; code rejects the price unless the quote is on the page. Currency is tagged per source and converted with a dated exchange rate. **No price comes from a model's memory.**
5. `finish_sweep.py`: builds `claim_packet.json` and `report.html`. Totals are computed in code. Empty fields mean unknown.

## Models and tools used
Gemini Live (gemini-3.8-live), Gemini 3.5 Flash and Flash-Lite, Firecrawl (search and scrape), Open Library, frankfurter.dev exchange rates, OpenCV, Python. Code written with AI assistance (Claude), tested by hand.

## Assumptions
- Country and currency defaulted to India and INR in tests; the live agent does not yet ask for them reliably.
- Glasses or earbuds worn by the person are not treated as room contents.
- A size is reported only if the book was measured in at least 2 frames and the values are plausible.

## What is not done
- No real-room capture of 60+ books on 2 shelving units with 8+ items, so the ground-truth sheet and accuracy table against the pass bars are incomplete.
- Room floor and wall area: not measured (skipped).
- Spine thickness fails the 15% bar (0 of 3 on a 480 px test video). Height was within 15% on 3 of 3. Only 3 books were hand-measured, not 20.
- Prices: the pipeline works (23 of 24 test books priced with sources) but Firecrawl free credits ran out, so the final sweep has no prices. No second-country test, no used values, no rare-book flagging.
- Non-book items: detection only, no prices, sizes empty, duplicates not fully merged.
- Voice corrections and coaching rely on the agent's instructions and were not tested properly.
- Cost per sweep and latency per stage were not measured.
- See `FAILURE_LOG.md`.

Phone note: the reference server rejects any Host that is not localhost or 127.0.0.1 (local_access in server.py), and its origin check compares the http scheme, so an https tunnel is blocked until both checks are patched to allow one specific tunnel host. The tunnel step was not completed or tested in this submission.

## Phone use (intended setup, not yet tested end to end)
The sweep is meant to run from a phone browser using the rear camera (the code requests facingMode environment). The backend runs on a laptop. Phone browsers only allow camera and microphone on https, so the local server would be exposed through an https tunnel (for example a cloudflared quick tunnel). A tunnel address gives access to the app and the API quota behind it, so it must stay private and be closed afterwards.
