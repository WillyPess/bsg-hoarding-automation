"""White tape (v1.1 rule 4, Gus 2026-11-01): rolls = total joint length / roll length, + 20% spare, rounded up.

Every joint counts:
  - vertical joints between sheets, corners and both run ends: full hoarding height each;
  - the joint between sheets and tops (along the whole run, when the job has tops);
  - the door: both sides (2 x door height) plus the top (door width).
All lengths in whole mm, so the rounding up is exact (no 3.0000000000000004 rolls)."""
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
        xs |= {mm(s["x"]), mm(s["x"] + SW)}
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
    sheet_h = mm(job.get("sheet_h", RULES["sheet"]["height"]))
    xs = vertical_joints(job, c)
    vertical = len(xs) * H
    tops = mm(c["L"]) if H > sheet_h and c["tops"] else 0
    door = 0
    if c.get("entry"):
        door = 2 * mm(job.get("door_height", DH)) + mm(c["entry"][1])
    total = vertical + tops + door
    return {"vertical_joints": len(xs), "vertical_mm": vertical, "tops_mm": tops, "door_mm": door,
            "total_mm": total, "rolls": rolls(total)}
