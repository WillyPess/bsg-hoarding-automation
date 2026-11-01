---
name: hoarding-corner-jobs
description: How corner-shop hoarding jobs (two faces + angled return) are handled; Shrungaar Hyperdome was the first
metadata:
  type: project
  modified: 2026-10-21T21:24:52.893Z
---

Corner shops (first one: Shrungaar, Hyperdome, 2026-10-21) use the same package as [[hoarding-job-package]], with job.json carrying a "faces" list left to right as seen from the mall: e.g. angled return, side, front (with "door_offset" from the corner), right return. Each face without a door has "cut": "left"/"right" = which end gets the cut piece (put it at the outside corner).

Scripts (in /mnt/project-files/hoarding/): layout_gen.py and materials.py accept faces (`materials.py out.xlsx <Job>/job.json`); package_gen.py has a corner branch (CN); sheet_corner.py draws the L-shaped plan + unfolded elevation. Uprights for corner jobs = 1 + sum(ceil(face/1.2)). Door studs are now "2 x <height>" (full height) + 4 x 2.3. Materials PDF: `soffice --headless --convert-to pdf`. Photo markup: <Job>/markup.py (Gus's outline, entry placed with a 1D perspective along the front).

Shrungaar facts (Gus): front 8.6 m, side 8.5 m, both returns 1.2 m (client asked; default 1.6 not used), height 4.0 m = 3.6 sheet + 400 top, entry 1.6 m with right end 4.8 m (so 2.2 m from the corner) because the shop entry has more room to the left. Angled return near the lift: angle not important, only show builders to keep clear of the lift. Outside corner treated as a normal joint until Gus's boss says otherwise. Result: 16 sheets in layout + 2 spare = 18, 15 tops x 400. Regenerated 2026-11-01 with uprights at sheet joins + weight matrix: 18 uprights, 6 per upright (4.2 m row), 119 counterweights incl. 10% spare.

Gus (2026-10-21): don't dimension the door height (2400) on the elevation; it is always the same. If a job uses a different door height, it comes with a note, so only show it then. sheet_corner.py no longer draws it.

Gus (2026-10-21): the melamine layout is a reference for the builders, not an exact build instruction, so small cut strips (e.g. Shrungaar's 100 mm S15b at the corner) are fine. Don't hold a job up asking about them.

U-shaped jobs (David Jones - Lift Area, 2026-11-01; external kiosk in a rooftop car park): job.json "shape": "U" with 5 faces (left return, left side, front, right side with door_offset from the front corner, right return), "sheet_h": 2.4 for 2.4 m jobs (2400 x 1200 sheets, no tops, entry full height). sheet_u.py draws the plan/elevation; package_gen has a UJ branch. DJ Lift: 1.6 + 5.6 + 10.2 + 5.6 + 1.6 = 24.6 m, 2.4 m high; Gus chose to keep the right side 5.6 with a full 1200 sheet right of the door, so the entry is 2800 from the front corner. 20 sheets + 2 spare, 24 uprights, 4 per upright, 106 weights. Gus's own photo markup used as-is.

External jobs (Gus, 2026-11-01, DJ Lift Area): the weight matrix is for internal hoardings. For wind Gus asked for **8 counterweights per upright and 40% more uprights** (rounded up; still +10% spare weights). job.json keys "weights_per_upright": 8 and "extra_uprights": 0.4, read by titan.for_job() in materials.py and package_gen.py. The extras aren't placed on the layout; the supervisor decides where. DJ Lift: 24 at joins + 10 extra = 34 uprights, 300 counterweights. Probably the rule for every external job, so confirm on the next one.
