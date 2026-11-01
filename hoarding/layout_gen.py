"""Melamine layout + cutting plan for any job. Full sheets first, cut pieces at the corners, one-piece door top.
Usage (corner jobs: add "faces", see faces()): layout_gen.py '{"title":"FRED","front":11.0,"return":1.6,"height":4.5,"door_offset":4.8,"door_width":1.6,"door_height":2.4}' out.png
Prints a JSON summary (sheets, tops, sheet pieces) used by package_gen.py."""
import sys, json, math
from PIL import Image, ImageDraw, ImageFont
SW, SH, TOPH = 1.2, 3.6, 0.9
E = 1e-6

def nfull(x): return int(round(x / SW, 6) // 1)

def ffd(rem):
    bins = []
    for r in sorted(rem, key=lambda r: -r["w"]):
        for b in bins:
            if b["left"] + E >= r["w"]: b["left"] = round(b["left"] - r["w"], 3); b["cuts"].append(r); break
        else: bins.append({"left": round(SW - r["w"], 3), "cuts": [r]})
    return bins

def faces(p):
    """Wall faces left to right, unfolded. Standard job: return / front / return. Corner jobs list p["faces"]:
    [{"name", "len", "cut": "left"|"right" (end for the cut piece), "door_offset" on the face with the entry}]."""
    if "faces" in p: return p["faces"]
    return [{"name": "left return", "len": p["return"], "cut": "right"},
            {"name": "front", "len": p["front"], "door_offset": p["door_offset"]},
            {"name": "right return", "len": p["return"], "cut": "left"}]

def runs(p):
    """Unfolded sections (x0, length, corner side, name), fold lines, dimension segments and the entry's x."""
    dw = p["door_width"]; secs, folds, segs, door_x, x = [], [], [], None, 0
    for f_ in faces(p):
        ln = f_["len"]
        if "door_offset" in f_:
            do = f_["door_offset"]; door_x = round(x + do, 3)
            secs += [(x, do, "left", f"{f_['name']} left"), (x + do + dw, ln - do - dw, "right", f"{f_['name']} right")]
            segs += [(x, x + do, None), (x + do, x + do + dw, "entry"), (x + do + dw, x + ln, None)]
        else:
            secs.append((x, ln, f_.get("cut", "right"), f_["name"])); segs.append((x, x + ln, f_["name"].replace("left ", "").replace("right ", "")))
        x = round(x + ln, 3); folds.append(x)
    return secs, folds[:-1], segs, door_x, x

def compute(p):
    global SH
    SH = p.get("sheet_h", 3.6)   # 2.4 m jobs (e.g. external, David Jones Lift Area) use 2400 x 1200 sheets, no tops
    dw = p["door_width"]
    secs, folds, segs, door_x, L = runs(p)
    full, rem = [], []
    for x0, ln, corner, name in secs:
        n = nfull(ln); r = round(ln - n * SW, 3)
        xs = x0 + (r if corner == "left" else 0)
        for i in range(n): full.append({"x": round(xs + i * SW, 3), "where": name})
        if r > E: rem.append({"x": round(x0 if corner == "left" else x0 + n * SW, 3), "w": r, "where": name})
    full.sort(key=lambda f: f["x"])
    for i, f in enumerate(full): f["sheet"] = i + 1
    bins = ffd(rem)
    k = len(full)
    for b in bins:
        k += 1; b["sheet"] = k
        for j, c in enumerate(b["cuts"]): c["sheet"] = k; c["label"] = f"S{k}" + ("abcdefgh"[j] if len(b["cuts"]) > 1 else "")
    door = None
    if dw > 0 and SH - p.get("door_height", 2.4) > E:
        k += 1; door = {"sheet": k, "x": door_x, "w": dw, "h": round(SH - p.get("door_height", 2.4), 3)}
    # tops: one above every sheet piece, same width, so every join runs in one line from floor to top (boss, 2026-10-21)
    TH = round(p["height"] - SH, 3)
    tfull = [{"x": f_["x"]} for f_ in full]
    for i, t_ in enumerate(tfull): t_["label"] = f"T{i + 1}"
    trem = [{"x": cu["x"], "w": cu["w"], "where": cu["where"]} for b in bins for cu in b["cuts"]]
    tbins = ffd(trem); kt = len(tfull)
    for b in tbins:
        kt += 1
        for j, cu in enumerate(b["cuts"]): cu["label"] = f"T{kt}" + ("abcdefgh"[j] if len(b["cuts"]) > 1 else ""); cu["n"] = kt
    if door and TH > E:   # top above the entry: one door_w x TH piece from the spare of the door-top sheet
        door["top_h"] = TH
        if round(door["h"] + TH, 3) > SW + E and round(2 * dw, 3) > SH + E: k += 1; door["top_sheet"] = k
        else: door["top_sheet"] = door["sheet"]
    # uprights stand at the joins between melamine sheets, never mid-sheet (Gus, 2026-11-01), so one each side of the entry too
    ed = {round(f_["x"], 3) for f_ in full} | {round(f_["x"] + SW, 3) for f_ in full}
    ed |= {round(cu["x"], 3) for b in bins for cu in b["cuts"]} | {round(cu["x"] + cu["w"], 3) for b in bins for cu in b["cuts"]}
    if door: ed |= {door_x, round(door_x + dw, 3)}
    ups = sorted(ed)
    if p.get("no_corner_uprights"): ups = [u for u in ups if all(abs(u - x) > E for x in [0, L] + folds)]   # no room in the corners (Medibank)
    if "track" in p:   # fire-door jobs: no uprights in the track + timbers section (from the wall end of that face)
        x0 = 0
        for f_ in faces(p):
            if f_["name"] == p["track"]["face"]: break
            x0 += f_["len"]
        ups = [u for u in ups if not (x0 - E <= u <= x0 + p["track"]["len"] + E)]
    return dict(L=L, folds=folds, segs=segs, full=full, bins=bins, door=door, entry=(door_x, dw) if door_x is not None and dw > 0 else None, tfull=tfull, tbins=tbins,
                sheets=k, tops=kt if TH > E else 0, uprights=ups)

def render(p, out):
    c = compute(p); H = p["height"]; L = c["L"]
    FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; FN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    f = lambda s, b=True: ImageFont.truetype(FB if b else FN, s)
    INK, GREY = (25, 28, 32), (120, 125, 130)
    pal = [(186,214,240),(190,230,200),(250,222,170),(222,200,240),(245,200,200),(200,232,232),(214,234,170),(240,210,230),
           (205,215,250),(255,236,120),(255,190,140),(170,220,200),(230,200,170),(200,200,240),(240,240,170),(190,225,240)]
    col = lambda n: pal[(n - 1) % len(pal)]
    W, Hc = 2400, 1900; im = Image.new("RGB", (W, Hc), "white"); d = ImageDraw.Draw(im)
    def t(xy, s, ft, fill=INK, a="mm"): d.text(xy, s, font=ft, fill=fill, anchor=a)
    mm = lambda v: f"{round(v * 1000):d}"
    tops_txt = f" + {c['tops']} tops 1.2 x {H - SH:.1f} m" if c["tops"] else ""
    t((80, 60), f"{p['title'].upper()}: MELAMINE LAYOUT ({c['sheets']} sheets 1.2 x {SH:g} m{tops_txt})", f(40), INK, "lm")
    t((80, 110), f"Sizes in mm. Same colour and number = cut from the same sheet. " + (", ".join(f"{fc['name']} {mm(fc['len'])}" for fc in faces(p)) if "faces" in p else f"Front {mm(p['front'])}, returns {mm(p['return'])}") + f", height {mm(H)}.", f(26, False), GREY, "lm")
    s = min(150, 2050 / L); X0 = 110; Yb = min(880, 240 + H * s); y36 = Yb - SH * s; yT = Yb - H * s; dh = p.get("door_height", 2.4); yD = Yb - dh * s
    t((80, 170), "ELEVATION (returns unfolded, seen from the mall)", f(28), GREY, "lm")
    def piece(x, w, y0, y1, fill, label, fs=None):
        a = (X0 + x * s, y0); b = (X0 + (x + w) * s, y1)
        d.rectangle([a, b], fill=fill, outline=INK, width=3)
        if label: t(((a[0] + b[0]) / 2, (y0 + y1) / 2), label, f(fs or (24 if w * s > 75 else 16)), INK)
    for fs_ in c["full"]: piece(fs_["x"], SW, y36, Yb, col(fs_["sheet"]), f"S{fs_['sheet']}")
    for b in c["bins"]:
        for cu in b["cuts"]: piece(cu["x"], cu["w"], y36, Yb, col(b["sheet"]), cu["label"] if cu["w"] * s >= 45 else "")
    small = sorted((cu for b in c["bins"] for cu in b["cuts"] if cu["w"] * s < 45), key=lambda cu: cu["x"]); lastx, row = -1e9, 0
    for cu in small:   # labels under narrow cuts; drop to a second line when two sit close together
        xm = X0 + (cu["x"] + cu["w"] / 2) * s; row = 1 - row if xm - lastx < 70 else 0; lastx = xm
        t((xm, Yb + 28 + row * 24), cu["label"], f(18), INK)
    dr = c["door"]
    if dr:
        piece(dr["x"], dr["w"], y36, yD, col(dr["sheet"]), f"S{dr['sheet']}  {mm(dr['w'])} x {mm(dr['h'])}", 20 if dr["w"] * s > 220 else 14)
        x0, x1 = X0 + dr["x"] * s, X0 + (dr["x"] + dr["w"]) * s
        d.rectangle([x0, yD, x1, Yb], fill="white", outline=INK, width=4)
        d.line([(x0, yD), (x1, Yb)], fill=INK, width=3); d.line([(x1, yD), (x0, Yb)], fill=INK, width=3)
        t(((x0 + x1) / 2, yD + 30), f"ENTRY {mm(dr['w'])} x {mm(dh)}", f(18 if dr["w"] * s > 220 else 13), INK)
    elif c.get("entry"):   # entry as high as the sheets: no door-top piece
        x0, x1 = X0 + c["entry"][0] * s, X0 + sum(c["entry"]) * s
        d.rectangle([x0, yD, x1, Yb], fill="white", outline=INK, width=4)
        d.line([(x0, yD), (x1, Yb)], fill=INK, width=3); d.line([(x1, yD), (x0, Yb)], fill=INK, width=3)
    if c["tops"]:
        for tp in c["tfull"]: piece(tp["x"], SW, yT, y36, (225, 225, 225), tp["label"], 22)
        for b in c["tbins"]:
            for cu in b["cuts"]: piece(cu["x"], cu["w"], yT, y36, (225, 225, 225), cu["label"] if cu["w"] * s >= 45 else "", 18)
        if dr and dr.get("top_h"): piece(dr["x"], dr["w"], yT, y36, col(dr["top_sheet"]), f"S{dr['top_sheet']}  {mm(dr['w'])} x {mm(dr['top_h'])}", 18 if dr["w"] * s > 220 else 13)
    for x in c["folds"]: d.line([(X0 + x * s, yT - 10), (X0 + x * s, Yb + 10)], fill=INK, width=7)
    for u in c["uprights"]:   # upright markers under the joins
        ux = X0 + u * s; d.polygon([(ux, Yb + 6), (ux - 11, Yb + 26), (ux + 11, Yb + 26)], fill=(30, 60, 170))
    t((X0 + L * s, Yb + 44), f"\u25b2 = upright ({len(c['uprights'])}), at the sheet joins", f(18), (30, 60, 170), "rm")
    d.rectangle([X0, yT, X0 + L * s, Yb], outline=INK, width=6)
    def hd(xa, xb, y, lab):
        a, b = X0 + xa * s, X0 + xb * s; d.line([(a, y), (b, y)], fill=INK, width=2)
        for xx in (a, b): d.line([(xx, y - 12), (xx, y + 12)], fill=INK, width=2)
        t(((a + b) / 2, y + 22), lab, f(22), INK)
    y = Yb + 70
    segs = [(a, b, f"{mm(b - a)} {k}" if k else mm(b - a)) for a, b, k in c["segs"]]
    for a, b, l in segs:
        if b - a > E: hd(a, b, y, l)
    hd(0, L, y + 70, mm(L))
    xr = X0 + L * s + 25
    for ya, yb, l in ([(yT, y36, mm(H - SH))] if c["tops"] else []) + [(y36, Yb, mm(SH))]:
        d.line([(xr, ya), (xr, yb)], fill=INK, width=2); [d.line([(xr - 12, yy), (xr + 12, yy)], fill=INK, width=2) for yy in (ya, yb)]
        t((xr + 12, (ya + yb) / 2), l, f(22), INK, "lm")
    # cutting plan
    Y0 = 1180; n = c["sheets"]; gap = min(205, 2250 / max(n, 1)); cs = min(120, (gap - 22) / SW); nf = 17 if gap > 160 else 13
    t((80, Y0 - 60), f"CUTTING PLAN: the {n} sheets", f(28), GREY, "lm")
    short = lambda w: w if gap > 160 else w.replace("left return", "L return").replace("right return", "R return").replace("front left", "front L").replace("front right", "front R")
    def sheet(i, cuts, note):
        x0 = 90 + (i - 1) * gap; h = SH * cs; w = SW * cs
        d.rectangle([x0, Y0, x0 + w, Y0 + h], fill=(245, 245, 245), outline=INK, width=3)
        for cx, cw, cy, ch, fill, l in cuts:
            a = (x0 + cx * cs, Y0 + cy * cs); b = (x0 + (cx + cw) * cs, Y0 + (cy + ch) * cs)
            d.rectangle([a, b], fill=fill or (245, 245, 245), outline=INK, width=2)
            if l: t(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), l, f(16), INK)
        t((x0 + w / 2, Y0 - 20), f"S{i}", f(24), INK)
        for k, line in enumerate(note): t((x0 + w / 2, Y0 + h + 24 + k * (24 if gap > 160 else 20)), line, f(nf, False), INK)
    for fs_ in c["full"]: sheet(fs_["sheet"], [(0, SW, 0, SH, col(fs_["sheet"]), "full")], ["full", fs_["where"]])
    for b in c["bins"]:
        cuts, x, note = [], 0, []
        for cu in b["cuts"]:
            cuts.append((x, cu["w"], 0, SH, col(b["sheet"]), mm(cu["w"]) if cu["w"] * cs >= 40 else "")); x += cu["w"]
            note.append(f"{mm(cu['w'])} {short(cu['where'])}")
        if b["left"] > E: cuts.append((x, b["left"], 0, SH, None, "")); note.append(f"({mm(b['left'])} spare)")
        sheet(b["sheet"], cuts, note)
    if dr:
        th = dr.get("top_h", 0) if dr.get("top_sheet") == dr["sheet"] else 0
        cuts = [(0, SW, SH - dr["w"], dr["w"], col(dr["sheet"]), "door")]
        note = [f"{mm(dr['w'])} x {mm(dr['h'])} door top"] if gap > 160 else ["door top", f"{mm(dr['w'])} x {mm(dr['h'])}"]
        if th: cuts.append((0, th, SH - 2 * dr["w"], dr["w"], col(dr["sheet"]), "top")); note += [f"{mm(dr['w'])} x {mm(th)} entry top"] if gap > 160 else ["entry top", f"{mm(dr['w'])} x {mm(th)}"]
        sp = round(SH - dr["w"] * (2 if th else 1), 3)
        cuts.append((0, SW, 0, sp, None, "")); note.append(f"turned; ({mm(sp)} spare)" if gap > 160 else f"({mm(sp)} spare)")
        sheet(dr["sheet"], cuts, note)
    if c["tops"]:
        nt = len(c["tfull"]); cut = [" + ".join(mm(cu["w"]) for cu in b["cuts"]) for b in c["tbins"]]
        msg = f"Each top is the same width as the sheet below it, so every join runs in one line. T1 to T{nt} are full 1200 x {mm(H - SH)}." + "".join(f" T{nt + i + 1} is cut {x}." for i, x in enumerate(cut))
        if dr and dr.get("top_h"): msg += f" Above the entry: {mm(dr['w'])} x {mm(dr['top_h'])} from S{dr['top_sheet']}."
        t((80, Hc - 40), msg, f(21, False), GREY, "lm")
    if dr: t((80, Hc - 85), f"Note: instead of cutting S{dr['sheet']}, the door-top pieces can be cut from a spare factory sheet and sent to the job. Send 2 extra sheets in case of damage.", f(21, True), INK, "lm")
    else: t((80, Hc - 85), "Send 2 extra sheets in case of damage.", f(21, True), INK, "lm")
    gapb = int(1080 - (Yb + 200))   # low hoardings: close up the empty band above the cutting plan
    if gapb > 100:
        im2 = Image.new("RGB", (W, Hc - gapb), "white"); im2.paste(im.crop((0, 0, W, int(Yb + 200))), (0, 0)); im2.paste(im.crop((0, 1080, W, Hc)), (0, int(Yb + 200))); im = im2
    im.save(out)
    return c

if __name__ == "__main__":
    c = render(json.loads(sys.argv[1]), sys.argv[2])
    print(json.dumps({"sheets": c["sheets"], "tops": c["tops"], "full": len(c["full"]),
                      "cuts": [[(cu["label"], cu["w"], cu["where"]) for cu in b["cuts"]] for b in c["bins"]],
                      "door": c["door"], "top_cuts": [[cu["w"] for cu in b["cuts"]] for b in c["tbins"]]}))
