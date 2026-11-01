# BSG Automation – v1 (2026-11-01)

Owner: **Gus** (BSG). Talk to Gus in Portuguese or English as he writes; documents and drawings are in English, sizes in **mm** on drawings.

## Goal

BSG supplies and installs **Titan hoardings** (free-standing 16 mm white melamine walls with taped joints, held up by Titan uprights + counterweights) in front of shops in shopping centres. This project replaces the hand work that Gus and his boss used to do for every job:

1. Mark the hoarding on a photo of the shopfront.
2. Draw the measured plan + elevation (boss's grid-paper style).
3. Plan the melamine sheets and cuts.
4. Fill in BSG's materials form.
5. Bundle it all into one **Hoarding Package PDF** for the install team.
6. For **Pacific Fair** jobs, make the **quotation** from BSG's rate card.

Everything lives in `/mnt/project-files/hoarding/` (scripts at the top, one folder per job).

---

## Business rules

Rules below were given or approved by Gus (or his boss). Don't invent new ones; when something isn't covered, ask Gus.

### 1. Photo markup (hoarding limit)
- Style copied from Gus's Just Cuts example: thin **red lines on the floor** of the photo, in perspective, from the shopfront corners out to the front line = the **hoarding limit**.
- A **box with a cross** = the **hoarding entry**. It must line up with the shop's own entrance (projected straight out onto the front line). The entry may shift a little to use full sheets (see §4).
- No dimensions on the photo.
- If Gus sends **his own marked-up photo, use it as-is** (Bikini, David Jones, Medibank, DJ Lift). Don't redraw. Keep extra marks he adds (e.g. a camera for centre management) and explain them with `photo_note` / `photo_text`.
- Sizes read only from a photo are **estimates**: mark them and ask Gus for the site measurements.

### 2. Plan + elevation (boss's grid sheet)
- One grid-paper sheet, sizes in mm, notes "* Total Length" and "* Height".
- **Plan:** the dashed red **lease line** = the shopfront (BSG can't access or fix to it). Black = hoarding. Returns run from the lease line to the front.
- **Elevation:** unfolded – left return | front | right return, entry drawn as a box with an X, dimensioned from the end of the front panel; the entry-offset dimension sits at mid-height of the entry.
- **Defaults:** return **1.6 m**; entry **1.6 m wide x 2.4 m high**, double doors swinging in.
- **Don't dimension the door height (2400)** – it's always the same. Only show it when a job note says it differs.
- Gus may give the entry position from either end; convert to `door_offset` from the left end of the front (or from the corner on corner/U jobs).

### 3. Materials form
- Copy **BSG's paper form exactly**: same sections (Titan, Board, Timber/Track, Doors & Securities, Tapes, Screws & Stickers, Tools), same rows, BSG CHK / INST CHK columns, "Materials checked by" box. Gus found a custom layout confusing – don't redesign it.
- Melamine: layout sheets **+ 2 spare sheets always** (damage on site).
- Door set is fixed: 2 doors 2340, deadbolt, 4 hinges, 4 metal plates. Door studs: **2 x full height + 4 x 2.3** (purpose of the 2.3 m studs still unknown).
- Studs, white tape and anti-tampers scale with run length (14 / 8 / 10 per 8.8 m, rounded up) – inferred from Just Cuts, not formally confirmed.

### 4. Melamine sheet layout
- Sheets are **1.2 m wide x 3.6 m high** (2.4 m jobs use 2400 x 1200 sheets and no tops – `sheet_h: 2.4`).
- Above 3.6 m: **tops** (1.2 x 0.9 m stock) up to the hoarding height.
- **Use as many full sheets as possible** (looks better); **push the cut pieces to the corners**. The entry may move off the shop entrance a little to make the front sections whole multiples of 1.2 m.
- **Combine offcuts** across sections to minimise sheets (e.g. three 400 pieces from one sheet).
- **Door top = ONE 1600 x 1200 piece** from a sheet turned sideways – never small slices. The top above it (1600 x 900) comes from the same sheet's spare.
- **Boss's rule:** top joins line up with the sheet joins below (one straight taped line floor to top); corner cut pieces get tops of the same width.
- Every package notes that the door-top pieces can be cut from a **spare factory sheet** instead.
- The layout is a **reference for the builders**, not an exact instruction: small cut strips (e.g. 100 mm) are fine, don't hold a job up over them.

### 5. Uprights (Titan)
- Uprights stand **at the joins between sheets, never mid-sheet**, including **one each side of the entry**. The layout marks them with blue ▲.
- Where a corner can't take an upright (fire-door jobs), use `no_corner_uprights`.

### 6. Counterweights – BSG weight matrix (internal hoardings)
By hoarding height (first row ≥ height), per upright, no bracing:

| Max height (m) | 1.2 | 1.8 | 2.4 | 3.0 | 3.6 | 4.2 | 4.8 | 5.4 | 6.0 | 6.6 | 7.2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Weights / upright | 2 | 3 | 4 | 4 | 5 | 6 | 7 | 8 | 9 | 11 | 12 |
| Upright centres | 2.4 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 |

**Always send +10% spare weights, rounded up.** (Code: `titan.py`.)

### 7. External jobs (wind) – David Jones Lift Area, Gus 2026-11-01
- The matrix is for internal hoardings. Outdoors: **8 counterweights per upright** and **40% more uprights** (rounded up), still +10% spare weights.
- The extra uprights aren't placed on the layout; the supervisor decides where.
- Probably the rule for every external job – confirm with Gus on the next one.

### 8. Corner shops (two faces + angled return) – first: Shrungaar, Hyperdome
- `faces` listed left to right as seen from the mall (e.g. angled return, side, front with `door_offset` from the corner, right return). Faces without a door get `cut: "left"/"right"` = end for the cut piece (outside corner).
- Angled return near a lift: angle not important, only keep clear of the lift. Outside corner treated as a normal joint until the boss says otherwise.
- Returns can differ from 1.6 m when the client asks (Shrungaar: 1.2 m).

### 9. U-shaped / kiosk jobs – first: David Jones Lift Area
- `shape: "U"` with 5 faces: left return, left side, front, right side (`door_offset` from the front corner), right return.

### 10. Fire-door jobs (narrow section) – first: Medibank, Pacific Fair
- Beside a fire door there's no room for uprights + counterweights. In that section use **90 mm steel track on the ceiling and floor** with **90x45 MGP10 timbers at 600 centres**; the melamine still goes full height.
- The track section stops short of the corner; uprights + counterweights carry on from there.
- **No uprights in the hoarding corners** (they don't fit).
- Don't draw fire-door clearance or track detailing (builders know how).
- **Every package carries the note:** "track + timbers is a suggestion only; BSG is still learning this method."
- Old track fixing marks on the ceiling show where it was done before.

### 11. Package PDF content
1. Hoarding limit on the photo · 2. Plan and elevation · 3. Melamine layout and cutting plan · 4. **Suggested Build Sequence** (for the install team only; step 1 = "Check the truck" incl. the 2 spares; no factory/loading steps; no diagonal-check sentence) · 5. Site checks · 6. Materials form.

### 12. Job site and quotations
- **For every job, ask Gus where it will be built.**
- **Pacific Fair** jobs get a quotation (done in the thread "Pacific Fair - Quotations"; Gus collects quotes there). Other sites: no quote process yet.
- Known sites: Pacific Fair = Medibank, FRED, David Jones Ground/First Level, David Jones Lift Area. Hyperdome = Bikini on the Beach, Shrungaar.
- **Rate card "BSG Hoarding Rate – Pacific Fair 25-26"** (effective 18/6/2025–30/6/2026, still current), ex GST per lineal metre:

| Height | 1.2 m kiosk | ≤2.4 | ≤3.6 | ≤4.2 | ≤4.8 | ≤6.0 | >6.0 |
|---|---|---|---|---|---|---|---|
| $/lm | 115 | 220 | 280 | 320 | 330 | 450 | **POA** |

- Pricing: lm = **full hoarding run incl. returns**; band = smallest height band ≥ job height; minimum 15 lm (kiosk) / 10 lm (others); add extras; then GST 10%.
- Included: 1 set of double doors (2340 x 1600, deadbolt by Pacific Fair + barrel bolt), engineering cert, drawing, up to 6 months on site.
- Extras: extra double doors $400/set during install, $800 after; passage set $50/set; post-install modification $800 min ($680 for hoardings before 1/10/2025), $100/h; cancellation $200 after 2 pm, $900 after 5 pm/dispatched, full cost if team on site. Scissor lift not included over 4.2 m. Public holiday, oversized transport and **wind-rated = POA** ("price on application": shown as a line with no price, not added to the total).
- Fire-door track sections: no extra charge for now. Quotes addressed to **GPT – Pacific Fair**. 2.4 m external kiosk hoarding uses the 2.4 m band, not the 1.2 m kiosk rate.
- Quote number `PF-<PREFIX>-<yymmdd>`, valid 30 days, job's grid sheet attached as last page.

---

## Scripts (`/mnt/project-files/hoarding/`)

| Script | What it does | Run |
|---|---|---|
| `layout_gen.py` | **Core engine.** `compute(job)` works out sections, full sheets, offcut bins, door top, tops and upright positions. CLI draws the melamine layout + cutting plan PNG and prints a JSON summary. | `layout_gen.py "$(cat job.json)" <P>_melamine_layout.png` |
| `titan.py` | Weight matrix, +10% spare, external-job overrides (`for_job`). Used by materials + package. | (library) |
| `materials.py` | Boss's materials form as xlsx (uses `compute` + `titan`). | `materials.py <P>_materials.xlsx job.json` |
| `sheet.py` | Grid sheet (plan + elevation, mm) for standard jobs (return/front/return). | `sheet.py '<json in mm>' <P>_hoarding_sheet.png` (front/return/height/door_* ×1000 + "title": "<TITLE>: HOARDING"; passing job.json in metres draws 0.0142 m) |
| `sheet_corner.py` | Grid sheet for corner jobs (L-plan + unfolded elevation). | `sheet_corner.py job.json <P>_hoarding_sheet.png` |
| `sheet_u.py` | Grid sheet for U-shaped/kiosk jobs. | `sheet_u.py job.json <P>_hoarding_sheet.png` |
| `sheet_firedoor.py` | Grid sheet for fire-door jobs (stepped lease line, track section). | `sheet_firedoor.py job.json <P>_hoarding_sheet.png` |
| `package_gen.py` | Builds `<P>_Hoarding_Package.pdf` (photo, sheet, layout, build sequence, site checks) and appends `<P>_materials.pdf`. Branches for corner / U / fire-door jobs. | `package_gen.py job.json` |
| `quotes/quote_gen.py` | Pacific Fair quotation PDF from the rate card (uses `quotes/bsg_logo.png`). | `quotes/quote_gen.py job.json [out.pdf]` |
| `cutplan.py` | Older offcut bin-packing, still imported by materials.py. | (library) |
| `drawings.py` | Earlier, cleaner plan/elevation in metres (supports `estimated[]` in amber). Not in the current package. | `drawings.py '<json>' out.png` |
| `layout.py`, `layout_fred.py`, `package_pdf.py` | **Legacy**, hard-coded for DeOnes / FRED. Superseded by `layout_gen.py` + `package_gen.py`. | – |
| `<Job>/markup.py` | Per-job photo markup with PIL (e.g. Shrungaar: outline from Gus's sketch, entry placed in 1D perspective along the front). | `python3 <Job>/markup.py` |
| `Medibank/track_plan.py` | One-off plan to check the track section with Gus. | – |

Dependencies: Python 3 with Pillow, openpyxl, reportlab, pypdf; LibreOffice (`soffice`) for xlsx → pdf. DejaVu fonts.

**Hoarding Planner** (browser tool): https://claude.ai/artifact/J3jGFh4YS9PkZyyuJRK88z – photo tab (scale reference, red hoarding lines, crossed door box, hatch, dims, text) and floor-plan tab (mm grid). Exports PNG with optional title block. Useful for marking a photo by hand.

---

## Job folder structure

```
hoarding/<Job>/
  job.json                       inputs (see below)
  <P>_photo.jpg|png              original photo (optional; when Gus sends a clean photo)
  <P>_hoarding_markup.jpg        photo with the hoarding limit + entry  (required by package_gen)
  <P>_hoarding_sheet.png         boss's grid sheet (plan + elevation)
  <P>_melamine_layout.png        sheet layout + cutting plan
  <P>_materials.xlsx / .pdf      materials form
  <P>_Hoarding_Package.pdf       final package for the install team
  <P>_Quotation.pdf              Pacific Fair only
  quote_extras.json              optional quote overrides (DJ Lift)
  markup.py / track_plan.py      optional job-specific scripts
```
`<P>` = `prefix` in job.json. Existing jobs: Bikini, DavidJones, DavidJones1, DavidJonesLift, FRED (old scripts) / FRED_v2 (current), Medibank, Shrungaar; DeOnes drafts sit in the top folder.

---

## How to reproduce (new job)

### Inputs from Gus
1. **Photo** of the shopfront (ideally already marked up by Gus).
2. **Shopfront width** (front), **height**, **returns** (default 1.6 m), **entry position** (from the left or right end; default entry 1.6 x 2.4 m).
3. **Job title** (exactly as Gus writes it) and **site** (ask – Pacific Fair needs a quote).
4. Anything special: corner shop, U-shaped/kiosk, fire door next to it, external (wind), different door height, marks on the photo.

### job.json
All lengths in **metres**. Standard job:
```json
{"name": "FRED", "prefix": "FRED_v2", "dir": "/mnt/project-files/hoarding/FRED_v2",
 "date": "01/11/2026", "title": "FRED", "site": "Pacific Fair",
 "front": 11.0, "return": 1.6, "height": 4.5,
 "door_offset": 4.8, "door_width": 1.6, "door_height": 2.4,
 "entry_note": ", set to use full sheets"}
```
Optional keys:
- Photo text: `photo_note` (line added under the photo), `photo_text` (replaces the caption), `photo_h` (photo height in mm on the page), `front_ends`, `by` (default "Gus").
- **Corner job:** `"faces": [{"name","len","cut"} ..., {"name":"front","len":..,"door_offset":..}]` (see `Shrungaar/job.json`).
- **U job:** `"shape": "U"`, 5 faces, `"sheet_h": 2.4` for 2.4 m hoardings (see `DavidJonesLift/job.json`).
- **External:** `"external": true, "extra_uprights": 0.4, "weights_per_upright": 8`.
- **Fire door:** `faces` (3), `"track": {"face","len","studs","lengths"}`, `"no_corner_uprights": true`, `"shopfront"`, `"step"`, `"push"`, `"right_return"` (see `Medibank/job.json`).
- **Quote:** `quote_no`, `quote_date`, `valid_days`, `kiosk`, `extra_doors`, `extra_doors_after`, `passage_sets`, `scope`, `extra_lines` [{desc, qty, unit, rate (null = POA)}], `price_notes`, `terms_notes`.

### Steps
```bash
H=/mnt/project-files/hoarding; J=$H/<Job>; P=<prefix>; cd $J
# 1. Photo markup -> ${P}_hoarding_markup.jpg  (Gus's own markup as-is, or a markup.py, or the Hoarding Planner)
# 2. Grid sheet (pick the one for the job type)
python3 $H/sheet.py "$(python3 -c "import json;j=json.load(open('job.json'));m={k:round(j[k]*1000) for k in ('front','return','height','door_offset','door_width','door_height')};m['title']=j['title'].upper()+': HOARDING';print(json.dumps(m))")" ${P}_hoarding_sheet.png   # standard (sheet.py is in mm)
python3 $H/sheet_corner.py job.json ${P}_hoarding_sheet.png          # corner   (or sheet_u.py / sheet_firedoor.py)
# 3. Melamine layout
python3 $H/layout_gen.py "$(cat job.json)" ${P}_melamine_layout.png
# 4. Materials form
python3 $H/materials.py ${P}_materials.xlsx job.json
soffice --headless --convert-to pdf ${P}_materials.xlsx
# 5. Package PDF (needs the 4 files above)
python3 $H/package_gen.py job.json
# 6. Pacific Fair only: quotation
python3 $H/quotes/quote_gen.py job.json
#    with overrides: merge quote_extras.json into the job first, e.g.
python3 -c "import json;j=json.load(open('job.json'));j.update(json.load(open('quote_extras.json')));json.dump(j,open('/tmp/q.json','w'))" && python3 $H/quotes/quote_gen.py /tmp/q.json ${P}_Quotation.pdf
```
Check the images (sheet, layout) before sending, and check the printed summary (sheets, tops, uprights, weights) against the rules above.

### Outputs
| File | For |
|---|---|
| `<P>_hoarding_markup.jpg` | Centre management / install team: where the hoarding goes |
| `<P>_hoarding_sheet.png` | Boss's measured plan + elevation |
| `<P>_melamine_layout.png` | Builders: sheet positions, cuts, tops, uprights ▲ |
| `<P>_materials.xlsx` / `.pdf` | Factory + installers checklist (sheets incl. 2 spare, tops, uprights, weights incl. 10%) |
| `<P>_Hoarding_Package.pdf` | Everything above + build sequence + site checks, one PDF |
| `<P>_Quotation.pdf` | Pacific Fair only: quote to GPT – Pacific Fair |

### Reference results (to sanity-check changes)
| Job | Run (m) | H | Sheets (layout+2) | Tops | Uprights | Weights | Quote ex GST |
|---|---|---|---|---|---|---|---|
| Bikini (Hyperdome) | 10.4 | 4.5 | 9+2 | 8 | 10 | 77 | – |
| FRED_v2 (PF) | 14.2 | 4.5 | 12+2 | 11 | 14 | 108 | $4,686 |
| David Jones Ground / First (PF) | 23.2 | 4.5 | 19+2 | 18 | 22 | 170 | $7,656 each |
| Shrungaar (corner, Hyperdome) | 19.5 | 4.0 | 16+2 | 15 x 400 | 18 | 119 | – |
| Medibank (fire door, PF) | 12.1 | 4.2 | 10+2 | 9 x 600 | 7 | 47 | $3,872 |
| DJ Lift Area (U, external, PF) | 24.6 | 2.4 | 20+2 | 0 | 24+10 = 34 | 300 | $5,412 + wind POA |

## Open points
- Purpose of the 4 x 2.3 m door studs (Gus to find out).
- External-job rule (8 weights, +40% uprights) to confirm on the next external job.
- Outside corners on corner jobs: normal joint until the boss says otherwise.
- No quotation process yet for sites other than Pacific Fair.
