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
python tests/update_baseline.py Medibank    # approve a changed drawing/document: writes out/Medibank/ and expected/Medibank/baseline.json
```

The lite bundle has no reference PDFs or PNGs, so `expected/<Job>/baseline.json` pins the outputs checked by eye on 2026-11-01: a hash of the pixels of every PNG and the text of every PDF page. Any change to a drawing or document fails `test_drawings_match_baseline` / `test_documents_match_baseline`. Check the new files by eye, then run `update_baseline.py` and commit the baseline change with the reason. The hashes depend on the pinned Pillow version and the fonts in `fonts/`.

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

| Job | Type | Site | Run (m) | H (m) | Sheets (layout+2) | Tops | Uprights | Weights | Quote ex GST |
|---|---|---|---|---|---|---|---|---|---|
| Bikini | standard | Hyperdome | 10.4 | 4.5 | 9+2 | 8 | 10 + 1 = 11 | 77 | – |
| FRED_v2 | standard | Pacific Fair | 14.2 | 4.5 | 12+2 | 11 | 14 + 2 = 16 | 108 | $4,686 |
| DavidJones (Ground) | standard | Pacific Fair | 23.2 | 4.5 | 19+2 | 18 | 22 + 3 = 25 | 170 | $7,656 |
| DavidJones1 (First) | standard | Pacific Fair | 23.2 | 4.5 | 19+2 | 18 | 22 + 3 = 25 | 170 | $7,656 |
| Shrungaar | corner | Hyperdome | 19.5 | 4.0 | 16+2 | 15 | 18 + 2 = 20 | 119 | – |
| Medibank | fire door | Pacific Fair | 12.1 | 4.2 | 10+2 | 9 | 7 + 1 = 8 | 47 | $3,872 |
| DavidJonesLift | U / kiosk, external | Pacific Fair | 24.6 | 2.4 | 20+2 | 0 | 24 + 10 + 4 = 38 | 300 | $5,412 + wind POA |

Uprights = joints (+ 40% for wind on external jobs) + 10% spare (v1.1 rule 1); the other v1.1 rules are listed in CLAUDE.md.

`FRED` (the first FRED run, 2026-10-20) is included for history only: its outputs come from the legacy scripts, before the spare-sheet, aligned-tops, uprights-at-joins and weight-matrix rules. **FRED_v2 is the fixture** for that job.

Good rounding cases for tests: `titan.for_job` (+10% weights rounded up: Bikini 10×7×1.1 = 77, Medibank 7×6×1.1 = 46.2 → 47; +40% uprights: 24×0.4 = 9.6 → 10), quote minimum lm (10 lm, 15 lm kiosk), height bands at the exact limits (4.2 m → $320 band, 2.4 m → $220 band), offcut packing (three 400 pieces from one sheet), and the 2.4 m job (sheet_h 2.4, no tops).

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
