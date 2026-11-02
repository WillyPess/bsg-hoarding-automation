"""White tape (v1.1 rule 4, Gus 2026-11-01): rolls = total joint length / roll length, + spare (100%, Gus 2026-11-02), rounded up.

Every joint counts:
  - vertical joints between sheets, corners and both run ends: full hoarding height each;
  - the joint between sheets and tops (along the whole run, when the job has tops);
  - the door: both sides (2 x door height) plus the top (door width).
All lengths in whole mm, so the rounding up is exact (no 3.0000000000000004 rolls).

Switch (rules.json tape.tape_rule): "joints" = the calculation above (Gus 2026-11-02); "v1" = 8 rolls per 8.8 m of run,
rounded up, kept to compare. rolls_for_job() is what the form and summary use.

Black skirting tape (Gus 2026-11-02, provisional): the full run lineal metres x (1 + spare) / roll length, rounded up."""
import math

from rules import RULES

SW = RULES["sheet"]["width"]
DH = RULES["defaults"]["door_height"]


def mm(x):
    return int(round(x * 1000))


def vertical_joints(job, c):
    """x (mm along the unfolded run) of every vertical joint: both run ends, the corners and every edge of a sheet
    piece or of the entry. On fire-door jobs this includes the joints without an upright (track section, corners)."""
    xs = {0, mm(c["L"])} | {mm(f) for f in c["folds"]}
    for s in c["full"]:
        xs |= {mm(s["x"]), mm(s["x"] + c["sheet_w"])}   # 2.4 m on a kiosk (sheets laid horizontally)
    for b in c["bins"]:
        for p in b["cuts"]:
            xs |= {mm(p["x"]), mm(p["x"] + p["w"])}
    if c.get("entry"):
        x, w = c["entry"]
        xs |= {mm(x), mm(x + w)}
    return sorted(xs)


def rolls(total_mm):
    """total joint length (mm) + spare, in rolls, rounded up."""
    spare_pct = int(round(RULES["tape"]["spare"] * 100))
    roll_mm = mm(RULES["tape"]["roll_length"])
    return -(-total_mm * (100 + spare_pct) // (100 * roll_mm))


def white_tape(job, c):
    H = mm(job["height"])
    sheet_h = mm(c["sheet_h"])   # stock sheet height by height band (rule 6)
    xs = vertical_joints(job, c)
    vertical = len(xs) * H
    tops = mm(c["L"]) if H > sheet_h and c["tops"] else 0
    door = 0
    if c.get("entry"):
        door = 2 * mm(job.get("door_height", DH)) + mm(c["entry"][1])
    total = vertical + tops + door
    return {"vertical_joints": len(xs), "vertical_mm": vertical, "tops_mm": tops, "door_mm": door,
            "total_mm": total, "rolls": rolls(total)}


def v1_rolls(c):
    """v1: materials.white_tape rolls per materials.per_length of run, rounded up (Just Cuts), exactly as before."""
    M = RULES["materials"]
    return math.ceil(M["white_tape"] * c["L"] / M["per_length"])


def rolls_for_job(job, c, rule=None):
    """White tape rolls for the form, by rules.json tape.tape_rule ("v1" or "joints"), or by `rule` when given."""
    rule = rule or RULES["tape"]["tape_rule"]
    if rule == "v1":
        return v1_rolls(c)
    if rule == "joints":
        return white_tape(job, c)["rolls"]
    raise ValueError(f'rules.json tape.tape_rule must be "v1" or "joints", not {rule!r}')


def black_rolls_mm(run_mm):
    """Black skirting tape rolls for a run length in mm: run x (1 + black_tape.spare) / black_tape.roll_length, rounded up."""
    B = RULES["black_tape"]
    spare_pct = int(round(B["spare"] * 100))
    return -(-run_mm * (100 + spare_pct) // (100 * mm(B["roll_length"])))


def black_tape(job, c):
    """Black skirting tape rolls: along the full lineal metres of the job (the whole run, returns and entry included)."""
    return black_rolls_mm(mm(c["L"]))
