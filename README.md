# BSG Hoarding Automation – v1 handoff, LITE version (2026-11-01)

> **Lite version for email.** Same engine, job.json files, docs and tests as the full `BSG_v1_handoff.zip`, but without the original photos, the expected PDFs/PNGs and `originals/`. The photo **markups** (`*_hoarding_markup.jpg`) stay in, because `package_gen.py` needs them to build the package. `check_fixtures.py` here checks the key counts (`expected_counts.json`) and every cell of the materials form; the PDF-text and image checks only run with the full bundle. Without `Shrungaar_photo.png`, `run_job.py` uses the existing Shrungaar markup instead of redrawing it.

The Python engine Gus uses for BSG's Titan hoarding jobs, the 7 reference jobs as inputs, and their expected outputs as test fixtures. The business rules and the meaning of every job.json key are in **CLAUDE.md** (read it first); background notes from the project are in **notes/**.

## Quick start

Needs Python 3.11+ (tested on 3.13) with `Pillow openpyxl reportlab pypdf`, LibreOffice (`soffice`, for xlsx → pdf) and the DejaVu fonts at `/usr/share/fonts/truetype/dejavu/` (Debian/Ubuntu: `fonts-dejavu-core`).

```bash
pip install pillow openpyxl reportlab pypdf
python3 check_fixtures.py              # runs all 7 jobs in temp folders and compares with expected/  → PASS/FAIL, exit code
python3 check_fixtures.py Medibank     # one job
python3 run_job.py hoarding/Bikini --out /tmp/Bikini   # full pipeline for one job, prints the key counts as JSON
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest                            # 7 reference jobs (counts, materials form, drawings, documents) + rounding traps, ~1 min
python -m pytest -k Medibank                # one job
python tests/update_baseline.py Medibank    # approve a changed drawing/document: writes out/Medibank/, expected/Medibank/baseline.json and png/
```

The lite bundle has no reference PDFs or PNGs, so the outputs checked by eye on 2026-11-01 are pinned in `expected/<Job>/`: the text of every PDF page (`baseline.json`) and every drawing as a PNG (`png/`). Any change fails `test_drawings_match_baseline` / `test_documents_match_baseline`. Check the new files by eye, then run `update_baseline.py` and commit the change with the reason.

**Drawings across machines.** Windows and Linux render text slightly differently, so drawings are not compared exactly. A pixel counts as changed when no pixel within 1 px of it in the baseline has every colour channel within 24. The test fails above **0.02 %** changed pixels and prints the % for every drawing (`pytest -s`); a failure saves `<name>_DIFF.png` with the changed pixels in magenta. 0.02 % is set to catch the smallest real change measured: the red lease line turned green is 0.05 %. A job without `png/` falls back to the exact pixel hash in `baseline.json`.

The stored PNGs were made on Linux. The hashes in `baseline.json` are still the ones approved on Windows. To store the Windows images instead: `python tests/update_baseline.py --store-pngs` (it stores only PNGs whose hash matches the approved one).

## Web app (in progress)

The app around the engine is being built step by step from `PLAN-app.md` (§11). Step 1, the skeleton, is in `app/`:

```bash
pip install -r requirements.txt
python -m app --check     # settings + health checks (data folder, config.toml, rules.json, LibreOffice, fonts)
python -m app.users add gus --role estimator     # asks for the password twice (at least 10 characters)
python -m app.users add boss --role manager
python -m app.users list                         # set-password <name> gives a new password and ends that user's sessions
python -m app             # serves http://127.0.0.1:8000 (this PC only); log in, then the health page is /health
```

Every page needs a login. Sessions end at logout, after 12 hours without use, or after 7 days. After 5 failed logins for a name in 15 minutes, that name can't log in for 15 minutes; after 20 failed logins from one address (on this PC, both users share 127.0.0.1), that address is locked for 15 minutes. So one person's typos don't lock the other out.

The data folder is `C:\BSG\data` on Windows (`~/BSG/data` elsewhere), or `BSG_DATA` when set. The first start writes `config.toml` there with every setting and its default (server address, AI model and cost caps); no secrets go in it. The AI reviewer stays off until it is built.

## Contents

| Path | What |
|---|---|
| `CLAUDE.md` | Full v1 documentation: business rules, scripts, job.json keys, how to reproduce, reference results |
| `notes/` | Project notes (corner jobs, fire-door jobs, quotation workflow, rate card, history of decisions) |
| `hoarding/*.py` | The engine. `layout_gen.py` (`compute()` = sheets, cuts, tops, upright positions) is the core; `titan.py` = weight matrix; `materials.py`, `sheet*.py`, `package_gen.py`, `quotes/quote_gen.py` |
| `hoarding/rules.json` | Every adjustable business value (sizes, spares, weight matrix, external values, defaults, rate card) with its source and whether it's provisional; the engine reads it through `hoarding/rules.py` |
| `hoarding/legacy/` | `layout.py`, `layout_fred.py`, `package_pdf.py`: old hard-coded scripts (DeOnes / FRED), superseded, kept for history only |
| `hoarding/<Job>/` | **Inputs** per job: `job.json`, the photo markup (`*_hoarding_markup.jpg`), photo, `quote_extras.json`, job scripts (`Shrungaar/markup.py`, `Medibank/track_plan.py`) |
| `expected/<Job>/` | **Fixtures**: outputs of the current engine from these inputs (materials xlsx/pdf, package PDF, quotation PDF, sheet + layout PNGs) and `run_summary.json` with the key counts |
| `expected/expected_counts.json` | The approved numbers per job (sheets, tops, uprights, weights, price) from CLAUDE.md – the real acceptance values |
| `originals/<Job>/` | The files exactly as delivered to Gus (some were made before later rule/wording changes, see below). Not for tests |
| `run_job.py` | Runs the pipeline for one job folder (picks the right grid sheet for standard / corner / U / fire-door jobs; quote only for Pacific Fair) |
| `check_fixtures.py` | Regression test: counts, every materials cell, PDF text page by page, PNGs pixel by pixel |

## The 7 reference jobs

| Job | Type | Site | Run (m) | H (m) | Sheets (layout+2) | Tops | Uprights | Anti-tampers | Weights | White tape | Black tape | Quote ex GST |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bikini | standard | Hyperdome | 10.4 | 4.5 | 9+2 | 8 | 10 + 1 = 11 | 11 | 11 x 7 = 77 | 5 | 1 | – |
| FRED_v2 | standard | Pacific Fair | 14.2 | 4.5 | 12+2 | 12 | 14 + 2 = 16 | 16 | 16 x 7 = 112 | 7 | 2 | $4,686 |
| DavidJones (Ground) | standard | Pacific Fair | 23.2 | 4.5 | 19+2 | 20 | 22 + 3 = 25 | 25 | 25 x 7 = 175 | 11 | 2 | $7,656 |
| DavidJones1 (First) | standard | Pacific Fair | 23.2 | 4.5 | 19+2 | 20 | 22 + 3 = 25 | 25 | 25 x 7 = 175 | 11 | 2 | $7,656 |
| Shrungaar | corner | Hyperdome | 19.5 | 4.0 | 16+2 | 16 | 18 + 2 = 20 | 20 | 20 x 6 = 120 | 8 | 2 | – |
| Medibank | fire door | Pacific Fair | 12.1 | 4.2 | 10+2 | 10 | 7 + 1 = 8 | 8 | 8 x 6 = 48 | 6 | 1 | $3,872 |
| DavidJonesLift | U / kiosk, external | Pacific Fair | 24.6 | 2.4 | 20+2 | 0 | 24 + 10 + 4 = 38 | 38 | 38 x 8 = 304 | 6 | 2 | $5,412 + wind POA |
| Bikini_3000 | test (rule 6) | Hyperdome | 10.4 | 3.0 | 9+2, cut to 3000 | 0 | 10 + 1 = 11 | 11 | 11 x 4 = 44 | 3 | 1 | – |
| Bikini_2400 | test (rule 6) | Hyperdome | 10.4 | 2.4 | 8+2, 2400 sheets | 0 | 10 + 1 = 11 | 11 | 11 x 4 = 44 | 3 | 1 | – |
| Kiosk_PF | test (rule 7), kiosk | Pacific Fair | 9.2 | 1.2 | 4+2, laid horizontally | 0 | 6 + 1 = 7 | 7 | 7 x 2 = 14 | 1 | 1 | $1,725 (15 lm min) |

Uprights = joints (+ 40% for wind on external jobs) + 10% spare (v1.1 rule 1); weights = all uprights x weights per upright, no separate +10% (rule 2); anti-tampers = uprights sent (rule 3); tops = pieces to cut from offcuts (rule 5); sheets by height band, cut down below 3.6 m (rule 6, test jobs Bikini_3000 / Bikini_2400); 1.2 m kiosk with sheets laid horizontally and one door cut in half (rule 7, test job Kiosk_PF); white tape = joint length x 2 / 25 m and black tape = run x 2 / 25 m (rule 4, Gus 2026-11-02; spares provisional). The other v1.1 rules are listed in CLAUDE.md.

`FRED` (the first FRED run, 2026-10-20) is included for history only: its outputs come from the legacy scripts, before the spare-sheet, aligned-tops, uprights-at-joins and weight-matrix rules. **FRED_v2 is the fixture** for that job.

Good rounding cases for tests: `titan.for_job` (+10% spare uprights rounded up: 14×0.1 = 1.4 → 2, Medibank 7×0.1 = 0.7 → 1; +40% uprights: 24×0.4 = 9.6 → 10, then 34×0.1 = 3.4 → 4 spare = 38; weights are whole numbers, all uprights x weights per upright), quote minimum lm (10 lm, 15 lm kiosk), height bands at the exact limits (4.2 m → $320 band, 2.4 m → $220 band), offcut packing (three 400 pieces from one sheet), and the 2.4 m job (sheet_h 2.4, no tops).

## Changes made for this handoff (vs the project folder)

- **job.json `dir`** is now relative (`hoarding/<Job>`); `run_job.py` replaces it with the absolute job folder, so the bundle runs from anywhere.
- Added **`site`** to every job.json, and a fixed **`quote_date`: 01/11/2026** to the Pacific Fair jobs so the quote number/date are reproducible (otherwise they use today's date). FRED_v2 also gets `quote_no: PF-FRED-261101` and `quote_file: FRED_Quotation.pdf`, as delivered.
- **Created `hoarding/FRED/job.json`** (the old FRED folder had none), from the known site measurements: front 11.0, returns 1.6, height 4.5, entry 4.8 m from the left. Marked `"legacy": true`.
- DeOnes (the first draft, estimated sizes, no job.json) is only in `originals/DeOnes_drafts/`; it is not a reference job.

## Where expected/ differs from originals/ (all explained, no number changed)

Reproduced from these inputs, every job matches the approved counts and its delivered materials form cell for cell; package and materials PDF text matches page by page. The only differences come from engine changes made after the file was delivered:
- **Medibank_Quotation.pdf**: one sentence reworded ("the returns and sides" instead of "the returns back to the shopfront"), changed for the U-shaped job. Same figures.
- **Bikini_hoarding_sheet.png**: the original still showed the 2400 door height, which the rule of 2026-10-21 removed.
- **DavidJones / DavidJones1 / Shrungaar melamine layout PNGs**: the empty band above the cutting plan is now closed up (shorter image), same content.
