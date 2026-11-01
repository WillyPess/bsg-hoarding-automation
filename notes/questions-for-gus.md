# Questions for Gus (2026-11-01)

Open points from v1.1 step D. **Answers from Gus on 2026-11-02 are marked at the top of each question.** For each one: what the engine does now, the options, and what changes in the numbers.
Numbers are from the 7 reference jobs (David Jones Ground and First are the same job, so they show once).
After the meeting, each answer becomes a value in `hoarding/rules.json` or a small PR, then the impact table is checked and the baseline approved.

---

## 1. White tape: the new joint calculation vs real use

> **Answered (Gus, 2026-11-02):** rolls are 25 m. The team always sends almost double, because changes on site mean removing tape and applying new; tape is cheap, so keep a big margin. **Decision: the joint calculation is switched on with a 100% spare** (the 100% is provisional until Gus's boss confirms it; it is on his list) (`tape.tape_rule = "joints"`, `tape.spare = 1.00`): Bikini 5, FRED 7, David Jones 11, Shrungaar 8, Medibank 6, DJ Lift 6 rolls.

**Now:** the form still uses v1: **8 rolls per 8.8 m of run**, rounded up. The new v1.1 calculation is in the code behind a switch (`rules.json` `tape.tape_rule`, PR #16). It works like this: total joint length (every vertical joint at full height + the sheets/tops joint + the door: 2 x door height + door width) + 20% spare, divided by 25 m rolls, rounded up.

| Job | v1 (on the form now) | New calculation | Joint length |
|---|---|---|---|
| Bikini | 10 | 3 | 61.8 m |
| FRED_v2 | 13 | 5 | 83.6 m |
| David Jones | 22 | 7 | 128.6 m |
| Shrungaar | 18 | 5 | 97.9 m |
| Medibank | 11 | 4 | 68.9 m |
| DJ Lift | 23 | 4 | 64.0 m |

The new calculation sends about a third of the v1 rolls.

**Question:** how many rolls did the team really use on a recent job (FRED or David Jones, if you know)?

**Options:**
- **a.** Keep v1 (no change).
- **b.** Switch to the new calculation (`"tape_rule": "joints"`). The numbers are in the table above.
- **c.** Use the new calculation with a bigger spare than 20%. Example for FRED (83.6 m): 50% spare gives 6 rolls, 100% gives 7.
- **d.** Is a roll really 25 m of usable tape? A shorter usable length gives more rolls.

---

## 2. White tape, reading A: are the door sides counted twice?

> **Answered (Gus, 2026-11-02):** a. the door sides count, as written (no code change).

The rule says: "vertical joints between sheets, corners and both run ends at full height" and "the door: both sides (2 x door height) plus the top". The two joints at the edges of the entry are already counted at full height (floor to top). So adding "both sides of the door" again counts 2 x 2.4 m = 4.8 m twice.

**Options:**
- **a.** As written: count both (what the code does now).
- **b.** The door adds only its top (door width), because its sides are already in the full-height joints.

| Job | a. as written | b. door top only |
|---|---|---|
| Bikini | 3 | 3 |
| FRED_v2 | 5 | **4** |
| David Jones | 7 | **6** |
| Shrungaar | 5 | 5 |
| Medibank | 4 | 4 |
| DJ Lift | 4 | **3** |

This only matters once question 1 switches to the new calculation.

---

## 3. White tape, reading B: does a full-height door have a top joint?

> **Answered (Gus, 2026-11-02):** a. the door top counts even when the door is full height, as written (no code change).

On DJ Lift (2.4 m hoarding), the entry is 2.4 m high, so nothing sits above the door. The rule adds "the top (door width)" = 1.6 m anyway.

**Options:**
- **a.** Always add the door top (what the code does now).
- **b.** Add it only when the hoarding is taller than the door.

DJ Lift goes **4 → 3 rolls** with b. No other job changes. With reading A as well, DJ Lift is still 3.

---

## 4. The 4 x 2.3 m door studs

> **Pending (2026-11-02):** Gus is asking his boss. No change: 4 x 2.3 m on every job.

**Now:** every job sends door studs = **2 x full height + 4 x 2.3 m** (BSG form, Just Cuts). Nobody knows what the 2.3 m studs are for.

- On 4.5 m jobs: "2 x 4.5 + 4 x 2.3" (6 studs).
- On DJ Lift (2.4 m hoarding): "2 x 2.4 + 4 x 2.3". Is a 2.3 m stud even needed when the hoarding is only 2.4 m high?

**Question (for the boss):** what are the 2.3 m studs for?

**Options:**
- **a.** Keep 4 x 2.3 on every job.
- **b.** They depend on the door (e.g. the frame around the 2340 leaves). Then kiosk doors (1.2 m) would need shorter studs or fewer.
- **c.** They depend on the hoarding height. Then 2.4 m jobs may not need them.

Only the "70 x 45 Door Studs" row on the form changes (now 6 on every job).

---

## 5. Official external-job table (wind)

> **Answered (Gus, 2026-11-02):** there is no official external table yet, only the internal matrix. **The provisional rule stays** (8 per upright, +40% uprights). No change.

**Now (provisional, DJ Lift):** **8 counterweights per upright** and **40% more uprights**. Then the 10% spare, then the extra weight % asked per job. DJ Lift: 24 joints → 24 + 10 = 34 → + 4 spare = **38 uprights, 304 counterweights**, 38 anti-tampers.

**Question:** did you get the official table (weights per upright and extra uprights for external hoardings)?

What changes for DJ Lift, as examples (uprights / weights; anti-tampers always = uprights):

| Weights per upright | +20% uprights | +40% uprights (now) | +60% uprights |
|---|---|---|---|
| 6 | 32 / 192 | 38 / 228 | 43 / 258 |
| 8 (now) | 32 / 256 | **38 / 304** | 43 / 344 |
| 10 | 32 / 320 | 38 / 380 | 43 / 430 |

The table goes into `rules.json` (`external`). If it depends on height or wind zone, it becomes a small table like the internal matrix (one PR).

---

## 6. Outside corners on corner jobs

> **Answered (Gus, 2026-11-02), provisional:** a. a normal joint with one upright, as the code does now. Provisional until his boss confirms. No change.

**Now:** an outside corner (Shrungaar) is a normal joint: one upright, tape at full height.

**Question (for the boss):** does an outside corner need anything more, such as a second upright, a corner trim, or extra weights?

**Options:**
- **a.** A normal joint (no change). Shrungaar: 18 joints → 20 uprights, 120 counterweights, 20 anti-tampers.
- **b.** One extra upright at each outside corner. Shrungaar: 19 joints → **21 uprights, 126 counterweights, 21 anti-tampers**.
- **c.** Something else, e.g. a corner trim (a new form row) or extra weights on the corner upright only.

---

## 7. Hoardings above 7.2 m

> **Still open (2026-11-02).** No change: the engine stops above 7.2 m.

**Now:** the weight matrix stops at 7.2 m (12 weights per upright, 1.2 m centres). A taller job stops the engine with "above the 7.2 m weight matrix". No job has gone above 7.2 m. The quote is already POA above 6.0 m.

**Question:** if one comes up, which calculation should we use?

**Options:**
- **a.** Stop and ask every time (now).
- **b.** An extra row, or rows, in the matrix from the official BSG or Titan table.
- **c.** Bracing or an engineer's design above 7.2 m: the engine flags it and leaves the weights blank.

---

## 8. The new Pacific Fair rate card

> **Answered (Gus, 2026-11-02):** the current card (25-26) stays. No change.

**Now:** "BSG Hoarding Rate – Pacific Fair 25-26" (validity ended 30/6/2026). You said on 2026-11-01 to keep using it until there is a new one.

Every quote is lm x $/lm for the height band, plus the extras, plus GST:

| Job | lm | Band | Quote ex GST now |
|---|---|---|---|
| FRED_v2 | 14.2 | ≤ 4.8 m, $330 | $4,686.00 |
| David Jones (each) | 23.2 | ≤ 4.8 m, $330 | $7,656.00 |
| Medibank | 12.1 | ≤ 4.2 m, $320 | $3,872.00 |
| DJ Lift | 24.6 | ≤ 2.4 m, $220 | $5,412.00 + wind POA |

**Question:** is there a 26-27 rate card yet? If yes: the new $/lm per band, the extras (doors, passage sets, modifications, cancellation), and the validity dates. It goes into `rules.json` (`rate_card`); every Pacific Fair quote changes by the same %. Example: +5% makes FRED $4,920.30.

---

## Also not formally confirmed (no question needed unless you want to check)

- **Studs: 14 per 8.8 m**, rounded up, inferred from Just Cuts (Bikini 17, FRED 23, David Jones 37, Shrungaar 32, Medibank 20, DJ Lift 40).
- **External jobs always 2.4 m** (v1.1 §7): the new-job form will check this, so tell us if an external job can ever be another height.

---

## 9. Black skirting tape (new, 2026-11-02)

> **Answered (Gus, 2026-11-02), provisional:** black tape is a skirt along the full lineal metres of the job. Rolls are 25 m. **Black tape = full run (returns and entry included) x 2 (100% spare, like the white tape) / 25, rounded up** (`rules.json` `black_tape`).

**Before:** a fixed 1 roll per job (Just Cuts form). **Now:** Bikini 1, FRED 2, David Jones 2, Shrungaar 2, Medibank 1, DJ Lift 2.
