"""Melamine cut plan: sheets 1.2 m wide x 3.6 m high. Reuses offcuts across wall sections."""
import math
SW = 1.2
def plan(sections, door_w, door_h=2.4, sheet_h=3.6, door_top="single"):
    # door_top "single" (Gus, 2026-10-20): one door_w x (sheet_h - door_h) piece cut from a sheet laid sideways; "strips" packs it into offcuts
    full, rem = 0, []
    for s in sections:
        n = int(round(s / SW, 6) // 1); full += n
        r = round(s - n * SW, 3)
        if r > 1e-6: rem.append(r)
    bins = []                                   # offcut sheets, first-fit decreasing
    for r in sorted(rem, reverse=True):
        for b in bins:
            if b["left"] + 1e-9 >= r: b["left"] = round(b["left"] - r, 3); b["cuts"].append(r); break
        else: bins.append({"left": round(SW - r, 3), "cuts": [r]})
    sheets = full + len(bins)
    # infill above the door, between door top and sheet top: strips of (sheet_h - door_h) high
    infill_h = sheet_h - door_h
    if infill_h > 0 and door_w > 0 and door_top == "single":
        sheets += 1
    elif infill_h > 0 and door_w > 0:
        per_strip = int(round(sheet_h / infill_h, 6) // 1)   # pieces one vertical strip yields
        spare_w = sum(b["left"] for b in bins)
        need_w = door_w / per_strip              # sheet width the infill consumes
        if spare_w + 1e-9 < need_w: sheets += math.ceil((need_w - spare_w) / SW)
    return sheets, full, bins
if __name__ == "__main__":
    for name, secs, dw in [("Just Cuts", [1.6, 0.4, 3.6, 1.6], 1.6), ("DeOnes", [1.6, 1.6, 3.8, 1.6], 1.6), ("FRED", [1.6, 4.8, 4.6, 1.6], 1.6)]:
        s, f, b = plan(secs, dw); print(name, "sheets", s, "full", f, "offcut sheets", [(x["cuts"], x["left"]) for x in b])
