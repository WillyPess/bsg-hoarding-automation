# BSG Automation – v1.1 (2026-11-01)

Owner: **Gus** (BSG). Talk to Gus in Portuguese or English as he writes; documents and drawings are in English, sizes in **mm** on drawings.

**Changes in v1.1 (Gus, 2026-11-01):** melamine sizes and tops from offcuts; heights between 2.4 and 3.6 m; kiosk sheets and doors; uprights, anti-tampers and white tape now calculated from joints; weights = all uprights (incl. spares) x weights per upright, no separate +10%; external jobs always 2.4 m, with an extra weight % asked per job; money rounded half a cent up; rate card kept until Gus says otherwise.

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

The numbers in these rules (sizes, spares, matrix, external values, defaults, rate card) live in **`hoarding/rules.json`**, each with its source and a `provisional` flag. Change a value there, not in the code, and update this file to match.

### 1. Photo markup (hoarding limit)

- Style copied from Gus's Just Cuts example: thin **red lines on the floor** of the photo, in perspective, from the shopfront corners out to the front line = the **hoarding limit**.
- A **box with a cross** = the **hoarding entry**. It must line up with the shop's own entrance (projected straight out onto the front line). The entry may shift a little to use full sheets (see §4).
- No dimensions on the photo.
- If Gus sends **his own marked-up photo, use it as-is** (Bikini, David Jones, Medibank, DJ Lift). Don't redraw. Keep extra marks he adds (e.g. a camera for centre management) and explain them with `photo_note` / `photo_text`.
- Sizes read only from a photo are **estimates**: mark them and ask Gus for the site measurements.

### 2. Plan + elevation (boss's grid sheet)

- One grid-paper sheet, sizes in mm, notes "\* Total Length" and "\* Height".
- **Plan:** the dashed red **lease line** = the shopfront (BSG can't access or fix to it). Black = hoarding. Returns run from the lease line to the front.
- **Elevation:** unfolded – left return | front | right return, entry drawn as a box with an X, dimensioned from the end of the front panel; the entry-offset dimension sits at mid-height of the entry.
- **Defaults:** return **1.6 m**; entry **1.6 m wide x 2.4 m high**, double doors swinging in.
- **Don't dimension the door height (2400)** – it's always the same. Only show it when a job note says it differs.
- Gus may give the entry position from either end; convert to `door_offset` from the left end of the front (or from the corner on corner/U jobs).

### 3. Materials form

- Copy **BSG's paper form exactly**: same sections (Titan, Board, Timber/Track, Doors & Securities, Tapes, Screws & Stickers, Tools), same rows, BSG CHK / INST CHK columns, "Materials checked by" box. Gus found a custom layout confusing – don't redesign it.
- **Melamine:** layout sheets **+ 2 spare sheets always** (damage on site).
- **Tops:** list only **how many tops to cut from offcuts, with their sizes**. Don't count them as new sheets. The person loading the truck decides whether to add new sheets (if a top size isn't in stock, they add one sheet per missing top). Step D rule 5, done: the form lists the pieces, e.g. Bikini "Tops from offcuts: 7 x 1200 x 900 + 1 x 400 x 900"; "Tops" = number of pieces (two pieces from one 1200 top count as two). The piece above the entry comes from the door sheet and is not listed.
- **Uprights = number of joints in the job + 10% spare, rounded up.** Both run ends count as joints. Fire-door jobs: only the joints where an upright actually stands (§10). External jobs: see §7.
- **Anti-tampers = 1 per upright, including the 10% spare uprights** (and the extra wind uprights on external jobs; step D rule 3, done). v1 sent 10 per 8.8 m of run.
- **Counterweights = all uprights (including the spare uprights) x weights per upright** (§6). No separate +10% spare weights.
- **White tape (rolls) = total joint length in metres / 25 m per roll, plus 100% spare, rounded up** (20% until Gus, 2026-11-02). Every joint counts:
  - vertical joints between sheets, corners and both run ends: **full hoarding height** each;
  - joints between sheets and tops;
  - the door: **both sides (2 x door height) plus the top (door width)**.
  - **Switched on (Gus, 2026-11-02):** `rules.json` `tape.tape_rule` = `"joints"` (this calculation, `hoarding/tape.py`, step D rule 4) with a **100% spare** (provisional until Gus's boss confirms it; rolls are 25 m; they always send almost double because changes on site mean removing tape and applying new, and tape is cheap). Readings A and B as written: the door sides count even though the entry joints are full height, and the door top counts even when the door is full height. `"v1"` (8 rolls per 8.8 m) stays in the switch to compare; the run summary shows `white_tape_rolls` (the form) and `white_tape_joints_rolls`.
- **Black skirting tape (rolls) = full run lineal metres (returns and entry included) x 2 (100% spare, like the white tape) / 25 m per roll, rounded up** (Gus, 2026-11-02, provisional; `rules.json` `black_tape`). v1 sent a fixed 1 roll per job.
- **Door set (normal job):** 1 double door = 2 leaves, each **0.8 m wide x 2.4 m high** (1.6 m total opening; form lists 2 doors 2340), deadbolt, 4 hinges, 4 metal plates. Door studs: **2 x full height + 4 x 2.3** (purpose of the 2.3 m studs still unknown).
- **Door set (1.2 m kiosk):** leaves are **0.8 m wide x 1.2 m high**; one normal door cut in half makes both leaves, so the form lists **1 door**.
- Studs scale with run length (14 per 8.8 m, rounded up) – inferred from Just Cuts, not formally confirmed.

### 4. Melamine sheet layout

- Melamine comes in **only two sizes: 2.4 m high x 1.2 m wide, and 3.6 m high x 1.2 m wide.** Sheets are cut or joined to make smaller or taller hoardings.
- **Height up to 2.4 m:** 2400 x 1200 sheets, no tops (`sheet_h: 2.4`).
- **Height over 2.4 m up to 3.6 m:** 3600 x 1200 sheets **cut down** to the hoarding height. The cut-off goes to **tops stock**, not waste.
- **Height over 3.6 m:** 3600 x 1200 sheets plus **tops** up to the hoarding height. Tops are cut from **offcuts of earlier jobs**, not bought as stock.
- **1.2 m kiosk:** 2400 x 1200 sheets **laid horizontally** (2.4 m long x 1.2 m high), no cut.
- **Use as many full sheets as possible** (looks better); **push the cut pieces to the corners**. The entry may move off the shop entrance a little to make the front sections whole multiples of 1.2 m.
- **Combine offcuts** across sections to minimise sheets (e.g. three 400 pieces from one sheet).
- **Door top = ONE 1600 x 1200 piece** from a sheet turned sideways – never small slices. The top above it (1600 x 900) comes from the same sheet's spare.
- **Boss's rule:** top joins line up with the sheet joins below (one straight taped line floor to top); corner cut pieces get tops of the same width.
- Every package notes that the door-top pieces can be cut from a **spare factory sheet** instead.
- The layout is a **reference for the builders**, not an exact instruction: small cut strips (e.g. 100 mm) are fine, don't hold a job up over them.

### 5. Uprights (Titan)

- Uprights stand **at the joins between sheets, never mid-sheet**, including **one each side of the entry**. The layout marks them with blue ▲.
- Count = joints (both run ends included) + 10% spare, rounded up (§3). Spare uprights aren't placed on the layout.
- Fire-door jobs: count only the joints where an upright actually stands, not the track section or the corners (Medibank: 7, plus the 10% spare).
- A hand-set `"uprights"` in job.json counts as the uprights at the joins; the 10% spare goes on top (12 → 14).
- Where a corner can't take an upright (fire-door jobs), use `no_corner_uprights`.

### 6. Counterweights – BSG weight matrix (internal hoardings)

By hoarding height (first row ≥ height), per upright, no bracing:

| Max height (m) | 1.2 | 1.8 | 2.4 | 3.0 | 3.6 | 4.2 | 4.8 | 5.4 | 6.0 | 6.6 | 7.2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Weights / upright | 2 | 3 | 4 | 4 | 5 | 6 | 7 | 8 | 9 | 11 | 12 |
| Upright centres | 2.4 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 |

**Weights to send = all uprights, including the 10% spare uprights, x weights per upright from the matrix** (Gus, 2026-11-01). Every spare upright gets the full counterweight set, so there is **no separate +10% spare weights** any more (v1 added 10% to the weights; removed in step D rule 2). No job has gone above 7.2 m; if one does, ask Gus which calculation to use.

### 7. External jobs (wind) – David Jones Lift Area, Gus 2026-11-01

- **External jobs are always 2.4 m high.**
- Provisional rule: **8 counterweights per upright** and **40% more uprights**. Round the 40% up first, then add the 10% spare uprights (§3) on that total, rounded up. DJ Lift: 24 joints → 24 + 10 = 34 → 34 + 4 = **38 uprights** (Gus confirmed 38). Weights = all uprights x 8 (§6): 38 x 8 = 304.
- The extra uprights aren't placed on the layout; the supervisor decides where.
- **Extra weight (Gus, 2026-11-01):** before computing counterweights for an external job, ask the user: "This job is external. Add extra weight? If yes, how many percent?" Apply only the percentage the user gives (default 0%), rounded up, and show it as a separate line in the summary and the materials form. **Never pick a percentage automatically.**
  - Applied **last, on the total weights** (all uprights incl. spares x 8), rounded up. It **adds to** the 8-per-upright rule; it doesn't replace it.
  - The answer is stored in job.json as `extra_weight_pct` (0 = no extra weight). `run_job.py` **stops and asks** when an external job doesn't have it; it never fills it in. DJ Lift: `"extra_weight_pct": 0`. Step D rule 8, done: the materials form shows an "Extra Counterweights" row on every external job (also at 0%, so the form shows the question was answered); the summary has `extra_weight_pct`, `extra_weights` and `total_weights_to_send`.
- **Not an official table.** Gus, 2026-11-02: there is no official external table yet, only the internal matrix, so this provisional rule stays. Replace it if one ever comes.

### 8. Corner shops (two faces + angled return) – first: Shrungaar, Hyperdome

- `faces` listed left to right as seen from the mall (e.g. angled return, side, front with `door_offset` from the corner, right return). Faces without a door get `cut: "left"/"right"` = end for the cut piece (outside corner).
- Angled return near a lift: angle not important, only keep clear of the lift. Outside corner = a normal joint with one upright, as the code does (Gus, 2026-11-02; provisional until his boss confirms).
- Returns can differ from 1.6 m when the client asks (Shrungaar: 1.2 m).

### 9. U-shaped / kiosk jobs – first: David Jones Lift Area

- `shape: "U"` with 5 faces: left return, left side, front, right side (`door_offset` from the front corner), right return.

### 10. Fire-door jobs (narrow section) – first: Medibank, Pacific Fair

- Beside a fire door there's no room for uprights + counterweights. In that section use **90 mm steel track on the ceiling and floor** with **90x45 MGP10 timbers at 600 centres**; the melamine still goes full height.
- The track section stops short of the corner; uprights + counterweights carry on from there.
- **No uprights in the hoarding corners** (they don't fit).
- Uprights count = only the joints where an upright actually stands, + 10% spare (§3). Medibank stays 7, plus spares.
- Don't draw fire-door clearance or track detailing (builders know how).
- **Every package carries the note:** "track + timbers is a suggestion only; BSG is still learning this method."
- Old track fixing marks on the ceiling show where it was done before.

### 11. Package PDF content

1. Hoarding limit on the photo · 2. Plan and elevation · 3. Melamine layout and cutting plan · 4. **Suggested Build Sequence** (for the install team only; step 1 = "Check the truck" incl. the 2 spares; no factory/loading steps; no diagonal-check sentence) · 5. Site checks · 6. Materials form.

### 12. Job site and quotations

- **For every job, ask Gus where it will be built.**
- **Pacific Fair** jobs get a quotation (done in the thread "Pacific Fair - Quotations"; Gus collects quotes there). Other sites: no quote process yet.
- Known sites: Pacific Fair = Medibank, FRED, David Jones Ground/First Level, David Jones Lift Area. Hyperdome = Bikini on the Beach, Shrungaar.
- **Rate card "BSG Hoarding Rate – Pacific Fair 25-26"**, ex GST per lineal metre. Its printed validity ended 30/6/2026, but **Gus confirmed on 2026-11-01 to keep using it** until he sends a new one (confirmed again 2026-11-02: the current card stays):

| Height | 1.2 m kiosk | ≤2.4 | ≤3.6 | ≤4.2 | ≤4.8 | ≤6.0 | >6.0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| $/lm | 115 | 220 | 280 | 320 | 330 | 450 | **POA** |

- Pricing: lm = **full hoarding run incl. returns**; band = smallest height band ≥ job height; minimum 15 lm (kiosk) / 10 lm (others); add extras; then GST 10%.
- Money: every line amount and the GST is rounded to the cent, **half a cent rounds up** (Gus, 2026-11-01). E.g. 10.125 lm x $330 = $3,341.25, GST $334.125 → $334.13.
- Included: 1 set of double doors (2340 x 1600, deadbolt by Pacific Fair + barrel bolt), engineering cert, drawing, up to 6 months on site.
- Extras: extra double doors $400/set during install, $800 after; passage set $50/set; post-install modification $800 min ($680 for hoardings before 1/10/2025), $100/h; cancellation $200 after 2 pm, $900 after 5 pm/dispatched, full cost if team on site. Scissor lift not included over 4.2 m. Public holiday, oversized transport and **wind-rated = POA** ("price on application": shown as a line with no price, not added to the total).
- Fire-door track sections: no extra charge for now. Quotes addressed to **GPT – Pacific Fair**. 2.4 m external kiosk hoarding uses the 2.4 m band, not the 1.2 m kiosk rate.
- Quote number `PF-<PREFIX>-<yymmdd>`, valid 30 days, job's grid sheet attached as last page.

---

## Scripts (`/mnt/project-files/hoarding/`)

| Script | What it does | Run |
| --- | --- | --- |
| `layout_gen.py` | **Core engine.** `compute(job)` works out sections, full sheets, offcut bins, door top, tops and upright positions. CLI draws the melamine layout + cutting plan PNG and prints a JSON summary. | `layout_gen.py "$(cat job.json)" <P>_melamine_layout.png` |
| `rules.json` / `rules.py` | Every adjustable business value with its source and `provisional` flag; `rules.py` loads the values as `RULES`. Entries with `used_from` are not read yet (step D). | (data) |
| `titan.py` | Weight matrix, external-job overrides (`for_job`). Used by materials + package. Uprights to send = joints + extra for wind + 10% spare (v1.1 rule 1, done); weights = all uprights x weights per upright, no separate +10% (rule 2, done). Extra weight on external jobs: `extra_weights` = the user's `extra_weight_pct` of the total weights, rounded up (rule 8, done). | (library) |
| `materials.py` | Boss's materials form as xlsx (uses `compute` + `titan`). Anti-tampers = uprights sent (v1.1 rule 3, done). Tops listed as pieces from offcuts (rule 5, done). White tape from joints + black tape from the run (rule 4 and Gus 2026-11-02, done). **Needs updating for v1.1:** kiosk door. | `materials.py <P>_materials.xlsx job.json` |
| `sheet.py` | Grid sheet (plan + elevation, mm) for standard jobs. | `sheet.py "$(cat job.json)" <P>_hoarding_sheet.png` |
| `sheet_corner.py` | Grid sheet for corner jobs. | `sheet_corner.py job.json <P>_hoarding_sheet.png` |
| `sheet_u.py` | Grid sheet for U-shaped/kiosk jobs. | `sheet_u.py job.json <P>_hoarding_sheet.png` |
| `sheet_firedoor.py` | Grid sheet for fire-door jobs. | `sheet_firedoor.py job.json <P>_hoarding_sheet.png` |
| `package_gen.py` | Builds `<P>_Hoarding_Package.pdf` and appends `<P>_materials.pdf`. | `package_gen.py job.json` |
| `quotes/quote_gen.py` | Pacific Fair quotation PDF from the rate card. | `quotes/quote_gen.py job.json [out.pdf]` |
| `cutplan.py` | Older offcut bin-packing, still imported by materials.py. | (library) |
| `drawings.py` | Earlier plan/elevation in metres. Not in the current package. | `drawings.py '<json>' out.png` |
| `layout.py`, `layout_fred.py`, `package_pdf.py` | **Legacy**, superseded by `layout_gen.py` + `package_gen.py`. | – |
| `<Job>/markup.py` | Per-job photo markup with PIL. | `python3 <Job>/markup.py` |
| `Medibank/track_plan.py` | One-off plan to check the track section with Gus. | – |

Dependencies: Python 3 with Pillow, openpyxl, reportlab, pypdf; LibreOffice (`soffice`) for xlsx → pdf. DejaVu fonts.

**Rounding:** use integer maths for every "rounded up" count (weights, uprights, sheets). In floating point, 50 x 1.1 = 55.000…01 and 21.6 / 1.2 = 18.000…004, which round up wrongly. Money is worked out in exact decimal and rounded to the cent, half a cent up (§12).

**Hoarding Planner** (browser tool): https://claude.ai/artifact/J3jGFh4YS9PkZyyuJRK88z – photo tab and floor-plan tab. Exports PNG with optional title block.

---

## Job folder structure

```
hoarding/<Job>/
  job.json                       inputs
  <P>_photo.jpg|png              original photo (optional)
  <P>_hoarding_markup.jpg        photo with the hoarding limit + entry  (required by package_gen)
  <P>_hoarding_sheet.png         boss's grid sheet (plan + elevation)
  <P>_melamine_layout.png        sheet layout + cutting plan
  <P>_materials.xlsx / .pdf      materials form
  <P>_Hoarding_Package.pdf       final package for the install team
  <P>_Quotation.pdf              Pacific Fair only
  quote_extras.json              optional quote overrides
  markup.py / track_plan.py      optional job-specific scripts
```

`<P>` = `prefix` in job.json.

---

## How to reproduce (new job)

### Inputs from Gus

1. **Photo** of the shopfront (ideally already marked up by Gus).
2. **Shopfront width**, **height**, **returns** (default 1.6 m), **entry position** (default entry 1.6 x 2.4 m; kiosk 1.6 x 1.2 m).
3. **Job title** and **site** (ask – Pacific Fair needs a quote).
4. Anything special: corner shop, U-shaped/kiosk, fire door, external (always 2.4 m; ask for the extra weight %, §7), marks on the photo.

### job.json

All lengths in **metres**. Standard job:

```json
{"name": "FRED", "prefix": "FRED_v2", "dir": "/mnt/project-files/hoarding/FRED_v2",
 "date": "01/11/2026", "title": "FRED", "site": "Pacific Fair",
 "front": 11.0, "return": 1.6, "height": 4.5,
 "door_offset": 4.8, "door_width": 1.6, "door_height": 2.4,
 "entry_note": ", set to use full sheets"}
```

Optional keys: `photo_note`, `photo_text`, `photo_h`, `front_ends`, `by`; corner `faces`; U `shape`, `sheet_h`; external `external`, `extra_uprights` / `weights_per_upright` (override rules.json for one job), `extra_weight_pct` (the user's answer, §7; required on external jobs: `run_job.py` stops and asks without it); fire door `faces`, `track`, `no_corner_uprights`, `shopfront`, `step`, `push`, `right_return`; hand-set `uprights` (uprights at the joins; the 10% spare goes on top, 12 → 14); quote `quote_no`, `quote_date`, `valid_days`, `kiosk`, `extra_doors`, `extra_doors_after`, `passage_sets`, `scope`, `extra_lines`, `price_notes`, `terms_notes`.

### Steps

```bash
H=/mnt/project-files/hoarding; J=$H/<Job>; P=<prefix>; cd $J
python3 $H/sheet.py "$(cat job.json)" ${P}_hoarding_sheet.png        # or sheet_corner / sheet_u / sheet_firedoor
python3 $H/layout_gen.py "$(cat job.json)" ${P}_melamine_layout.png
python3 $H/materials.py ${P}_materials.xlsx job.json
soffice --headless --convert-to pdf ${P}_materials.xlsx
python3 $H/package_gen.py job.json
python3 $H/quotes/quote_gen.py job.json                              # Pacific Fair only
```

Check the images and the printed summary against the rules above before sending.

### Reference results (v1.1 rules 1–5 and 8 applied)

Uprights = joints (+ extra for wind) + 10% spare (v1.1 rule 1). Weights = all uprights x weights per upright, no separate +10% (rule 2). Anti-tampers = 1 per upright sent (rule 3). Tops = pieces to cut from offcuts (rule 5). White tape = joint length x 2 / 25 m, black tape = run x 2 / 25 m (rule 4, Gus 2026-11-02; both spares provisional). The next v1.1 rules (6, 7) change the sheets and the kiosk door; update these rows with each rule.

| Job | Run (m) | H | Sheets (layout+2) | Tops | Uprights | Anti-tampers | Weights | White tape | Black tape | Quote ex GST |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bikini (Hyperdome) | 10.4 | 4.5 | 9+2 | 8 | 10 + 1 = 11 | 11 | 11 x 7 = 77 | 5 | 1 | – |
| FRED\_v2 (PF) | 14.2 | 4.5 | 12+2 | 12 | 14 + 2 = 16 | 16 | 16 x 7 = 112 | 7 | 2 | $4,686 |
| David Jones Ground / First (PF) | 23.2 | 4.5 | 19+2 | 20 | 22 + 3 = 25 | 25 | 25 x 7 = 175 | 11 | 2 | $7,656 each |
| Shrungaar (corner, Hyperdome) | 19.5 | 4.0 | 16+2 | 16 x 400 | 18 + 2 = 20 | 20 | 20 x 6 = 120 | 8 | 2 | – |
| Medibank (fire door, PF) | 12.1 | 4.2 | 10+2 | 10 x 600 | 7 + 1 = 8 | 8 | 8 x 6 = 48 | 6 | 1 | $3,872 |
| DJ Lift Area (U, external, PF) | 24.6 | 2.4 | 20+2 | 0 | 24 + 10 + 4 = 38 | 38 | 38 x 8 = 304 | 6 | 2 | $5,412 + wind POA |

## Open points

- Purpose of the 4 x 2.3 m door studs (pending 2026-11-02: Gus is asking his boss).
- Official external-job table: none exists yet (Gus, 2026-11-02); the provisional rule stays (§7).
- Outside corners on corner jobs: normal joint with one upright (Gus, 2026-11-02), provisional until his boss confirms.
- White tape spare (100%): provisional until Gus's boss confirms it (on his list).
- Black tape rolls (25 m, x2 spare): provisional (Gus, 2026-11-02).
- Hoardings above 7.2 m: never happened; Gus will give the calculation if one comes up.
- New Pacific Fair rate card: the current one stays (Gus, 2026-11-02); Gus will send a new one when there is one.
- No quotation process yet for sites other than Pacific Fair.
