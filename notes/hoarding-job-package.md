---
name: hoarding-job-package
description: What to deliver for each new BSG hoarding job from a shopfront photo, and the scripts that make each piece
metadata:
  type: project
---

Gus's standard package per job (agreed 2026-10-13 on DeOnes):
1. **Red-line photo markup** in the JustCuts style: the hoarding limit on the floor and a crossed entry box lined up with the shop entry. Drawn with PIL.
2. **Grid sheet** in the boss's style: plan plus unfolded elevation, in mm. Use /mnt/project-files/hoarding/sheet.py; drawings.py is the earlier, cleaner variant.
3. **Materials list** on the boss's form: /mnt/project-files/hoarding/materials.py, which uses cutplan.py. Args: out, job, front, return, height, door_offset, door_width.
4. **Melamine layout and cutting plan**: layout.py (DeOnes positions are currently hard-coded and need adapting per job).

Defaults:
- return 1.6 m
- hoarding entry 1.6 m wide x 2.4 m high, lined up with the shop entry
- melamine 1.2 x 3.6 m, with 1.2 x 0.9 m tops to 4.5 m

Sizes that come only from a photo are estimates. Mark them and ask for the site measurements: front width, height, entry offset. See [[hoarding-measured-drawings]] and [[hoarding-planner-artifact]].

FRED (2026-10-13): Gus confirmed the photo markup. The package lives in /mnt/project-files/hoarding/FRED/. It is the first job with a build guide, written as a Claude Doc "FRED Hoarding: Build Guide" at https://claude.ai/code/artifact/ac872d37-42a7-4677-a42b-39a88c9a63f3. persp.py fits the camera from the two base corners, the facade top line and the known front width, so the entry projects correctly onto an angled photo. layout_fred.py is the FRED-specific melamine layout. FRED final (2026-10-20): entry 4.8 m from the left end of the front (4800 to 6400), sections 1.6 / 4.8 / entry 1.6 / 4.6 / 1.6, 12 sheets + 12 tops.

Gus's layout rules (2026-10-20): **use as many full sheets as possible** and put cut pieces at the corners; the entry may shift off the shop entry to make the front sections whole multiples of 1.2 m. **Door top is ONE 1600 x 1200 piece** cut from a sheet turned sideways (cutplan.py door_top="single", +1 sheet), never offcut strips. In the boss's grid sheet the entry offset dimension sits at mid-height of the entry, not on the floor line (sheet.py).

**Generic pipeline (2026-10-20), use for every new job:** put a job.json in /mnt/project-files/hoarding/<Job>/ (name, prefix, dir, date, front, return, height, door_offset, door_width, door_height, title), then run sheet.py (mm), materials.py, `layout_gen.py '<json>' <Job>/<prefix>_melamine_layout.png` (full sheets first, cuts at corners, one-piece door top) and `package_gen.py <Job>/job.json`. These replace the hard-coded layout_fred.py and package_pdf.py. Bikini on the Beach (2026-10-20): Gus drew the photo markup himself; 8.0 m front, 1.2 m returns, 4.5 m high, entry 1.2 m from the left (read off his box, all full sheets), 9 sheets + 9 tops.

Boss's rule (2026-10-21): **top joins line up with the sheet joins** (tape runs one straight line floor to top). layout_gen.py puts one top above every sheet piece at the same width (cut tops packed from 1.2 x 0.9 tops), and the top above the entry is one door_width x 0.9 piece cut from the spare of the door-top sheet. materials.py now takes sheets and tops from layout_gen.compute. Bikini: 9 sheets + 8 tops.

Gus (2026-10-21): **always order 2 extra 3.6 m sheets** for damage (materials.py SPARE=2; the layout still shows only the sheets it uses). Every package notes that the door-top pieces can be cut from a spare factory sheet instead of cutting the door-top sheet (BSG has plenty of spares). Bikini: 9 in the layout + 2 spare = 11 sheets, 8 tops.

Gus (2026-10-21), build steps: section is titled "Suggested Build Sequence" and is written for the install team only (a different team loads the truck), so no factory pre-cut or loading steps; step 1 is "Check the truck" (install team checks everything was loaded, incl. the 2 spares) before leaving. No diagonal-check sentence (confusing).

Door studs (2026-10-21): 2 x 4.5 m = full-height studs each side of the entry (Gus agreed). The purpose of the 4 x 2.3 m studs is unknown; Gus will find out. Until then the build steps just list them.

David Jones - Ground Level (2026-10-27): 20 m front, 4.5 m high, entry 6000 from the right end (12.4 m from left), returns not given so default 1.6 m used; 19 layout sheets + 2 spare, 18 tops. Files in hoarding/DavidJones/. Gus gives entry position from either end; convert to door_offset from the left.

David Jones - First Level (2026-10-27): 20 m front, 4.5 m, entry 7200 from right (11.2 m from left), 1.6 m returns, 19 + 2 spare sheets, 18 tops; hoarding/DavidJones1/. Gus marks extras like a camera on the photo for centre managers: keep the mark, don't change the hoarding; job.json "photo_note" adds a line under the photo.

Workflow (Gus, 2026-11-01): for every job, ask Gus where it will be built. If it is at Pacific Fair, send the finished package (job.json, measurements, materials, PDF paths) to the "Pacific Fair - Quotations" thread (root cmsg_01PTabfBK11vCk1sBQenAwwR8CiAwxz7PVHgbaxAzPRDY7), which makes the quote from BSG's Pacific Fair rate PDF; Gus collects the quote there.
