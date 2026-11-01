---
name: hoarding-measured-drawings
description: BSG's second drawing per job (plan + unfolded elevation with measurements) and the generator script
metadata:
  type: project
  modified: 2026-10-13T20:48:33.587Z
---

Each hoarding job gets a second drawing with measurements. The layout comes from Gus's Just Cuts sketch (2026-10-13). The header gives H (hoarding height) and Length (return + front + return).
- **PLAN:** The red **lease line** is the shopfront, which BSG cannot access. It is hatched on the shop side and the shop entry is marked on it. The black lines are the hoarding limit. Each side **return** runs from the lease line to the front melamine and was 1.6 m on Just Cuts. The front carries a 1.6 m wide, 2.4 m high (Gus confirmed) double-door hoarding entry, lined up with the shop entry, and the doors swing inward.
- **ELEVATION:** The returns are unfolded either side of the front and the entry is shown. Dimensions run along the bottom. On Just Cuts these were 1.6 | 0.4 | 1.6 door | 3.6 | 1.6 = 8.8 m, with H 4.5 m.

The generator is /mnt/project-files/hoarding/drawings.py. It takes a JSON argument: front, return, height, door_offset, door_width, door_height and estimated[]. Values listed in estimated[] are drawn amber with a * mark.

**Why:** Gus wants these produced without drawing them by hand. **How to apply:** ask for the site measurements, and never present estimated sizes as final. Related: [[hoarding-planner-artifact]]

Boss's version (2026-10-13): a single grid-paper sheet with sizes in mm. It has the notes "* Total Length", "* Height", a small plan with a dashed lease line, and an unfolded elevation dimensioned return/front/return with the height. The entry is drawn as a 1600-wide box with an X, dimensioned from the end of the front panel (600 on Just Cuts). Generator: /mnt/project-files/hoarding/sheet.py (same JSON args as drawings.py, sizes in mm).

Materials list (2026-10-13): this is BSG's printed checklist form. Its sections are Titan, Board, Timber/Track, Doors & Securities, Tapes, Screws & Stickers and Tools. /mnt/project-files/hoarding/materials.py takes the arguments out.xlsx, job, front, return and height (m). It builds an xlsx laid out exactly like the boss's paper form, because Gus found an extra-column layout confusing.

The rules below are inferred from Just Cuts (8.8 m x 4.5 m) and not yet confirmed by Gus:
- uprights = ceil(L/1.2)+1, with 6 counterweights each
- melamine sheets are 3.6 m high x 1.2 m wide. **Minimise sheets by reusing offcuts** (Gus, 2026-10-13). Example: three 1.6 m sections = 3 full sheets + 3x0.4 m from one more = 4 sheets. cutplan.py fills each section (returns, left of door, right of door) with full sheets, bin-packs the remainders and fits the above-door infill into spare offcut. Gus (2026-10-13): above the door use 1.2 m tops (door top up to 3.6 m), then 900 mm tops to 4.5 m along the run; Agreed for DeOnes on 2026-10-13: 8 sheets with an offcut door top; SUPERSEDED 2026-10-20: the door top is now one 1600 x 1200 piece from its own sheet (see [[hoarding-job-package]]).
- MGP10 studs, white tape and anti-tampers scale by L/8.8
- the door set (2 doors 2340, deadbolt, 4 hinges, 4 plates, door studs 2x4.5 + 4x2.3) is fixed
- the tools are fixed
