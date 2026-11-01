---
name: hoarding-fire-door-jobs
description: Hoarding beside fire doors uses ceiling+floor steel tracks with timbers instead of uprights/counterweights (Medibank Pacific Fair first, 2026-10-27)
metadata:
  type: project
  modified: 2026-10-27T23:50:59.509Z
---

Gus (2026-10-27): when a shop sits right next to a fire door, the narrow section beside it has no room for uprights + counterweights. There, steel track (e.g. Siniat 92 mm x 3000 mm 0.50 BMT wall track, Bunnings) is fixed to the ceiling and the floor, and timbers in the tracks hold the melamine. Uprights resume right after that section, before the corner. Evidence of an earlier install: old track fixing marks on the ceiling/bulkhead.

First example: Medibank, Pacific Fair (photo: the fire door is on the left, the left return runs beside it, the entry is at the right end of the front).

Gus's answers (2026-10-28):
- The track section stops short of the front corner. An upright sits on the return between the track section and the corner, and uprights + counterweights carry on from there.
- Track: 90 mm steel track, one on the ceiling and one on the floor. Studs: 90x45 MGP10 at 600 centres (for now).
- The melamine in the track section goes to the full hoarding height, the same as the rest.
- Don't draw the fire door clearance or any special track detailing: the builders know how. No hatched band is needed on the boss's sheets.
- No uprights in any corner, including where a return meets the shopfront: they can't fit there (Medibank; probably general).
- Every package must carry a note that track + timbers is a suggestion only, because BSG is still learning this method.

Medibank Pacific Fair measurements: height 4200, left return 3000 (track section + upright), shopfront 7200, right return 1600. Files: /mnt/project-files/hoarding/Medibank/ (track_plan.py makes the plan for checking). Geometry (Gus, 2026-10-28; my first try with an angled front was wrong): the front hoarding is straight and parallel to the shopfront. The shop's lease line sits 1400 in front of the fire door wall, so the left return is 3000 from the wall and the right return is 1600 from the lease line. The left return is pushed a bit to the left of the shop (300 was my guess). Agreed layout (Gus, 2026-10-28): tracks over the 1400 alcove beside the fire door; on the left return, one upright in line with the shopfront and one in the middle of the remaining 1600. **No uprights in the hoarding corners (they don't fit there).** I spread the front uprights between the corners (6) and gave the right return a single upright in its middle, with none at either end (Gus asked for the same no-corner idea there). Gus approved this plan on 2026-10-28 (Medibank_track_plan_CHECK.png). Gus confirmed the 300 push and the entry 1200 from the right end (front 7500, so door_offset 4700). Package delivered 2026-10-28: 10 sheets in the layout + 2 spare, 9 tops x 600, 2 x 3.0 m track, 3 x 90x45 x 4.2.
Tooling: put "track" {face, len, studs, lengths}, "no_corner_uprights": true, "shopfront", "step", "push" and "right_return" in job.json, with 3 "faces". materials.py fills the 90mm track and 90x45 rows and adds the suggestion note. package_gen.py has an FD branch (set-out, track step, upright positions, checks). sheet_firedoor.py draws the stepped-lease-line plan and elevation. **Photo: use Gus's own marked-up photo as-is; don't draw my own markup (Gus, 2026-10-28).** Set photo_text in job.json for the caption.
Update 2026-11-01: uprights must sit at the sheet joins, so Medibank now has 7: left return at 2400 from the wall (the 1200 join falls on a track timber), front at 1100/2300/3500/4700/6300, right return at 400 from the front corner. This replaces the mid-1600 positions.
Related: [[hoarding-job-package]], [[hoarding-corner-jobs]].
