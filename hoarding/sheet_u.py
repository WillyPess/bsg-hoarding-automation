"""U-shaped hoarding (round three sides of a kiosk) in the boss's grid-paper layout: plan (left) + unfolded elevation (right), mm.
Usage: sheet_u.py job.json out.png   (job.json "faces": left return, left side, front, right side (door_offset from the front corner), right return)"""
import sys, json
from PIL import Image, ImageDraw, ImageFont
from paths import F, FB
fnt = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
INK, BLUE, RED, GREY = (20, 22, 26), (30, 60, 170), (190, 30, 60), (110, 115, 120)

def render(p, out):
    fa = p["faces"]; lr, ls, fr, rs, rr = [f["len"] for f in fa]
    doff, dw, dh, H = fa[3]["door_offset"], p["door_width"], p["door_height"], p["height"]
    total = sum(f["len"] for f in fa)
    W, Hc, G = 2400, 1600, 40
    im = Image.new("RGB", (W, Hc), (252, 252, 250)); d = ImageDraw.Draw(im)
    for x in range(0, W, G): d.line([(x, 0), (x, Hc)], fill=(196, 214, 232) if x % (G * 5) else (160, 186, 214), width=1)
    for y in range(0, Hc, G): d.line([(0, y), (W, y)], fill=(196, 214, 232) if y % (G * 5) else (160, 186, 214), width=1)
    def t(xy, s, f, fill, anchor="mm", rot=0):
        if not rot: d.text(xy, s, font=f, fill=fill, anchor=anchor); return
        box = d.textbbox((0, 0), s, font=f); tw, th = box[2] - box[0] + 8, box[3] - box[1] + 12
        tim = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); ImageDraw.Draw(tim).text((tw / 2, th / 2), s, font=f, fill=fill, anchor="mm")
        tim = tim.rotate(rot, expand=True); im.paste(tim, (int(xy[0] - tim.width / 2), int(xy[1] - tim.height / 2)), tim)
    def hdim(xa, xb, y, v, above=True, sz=28):
        d.line([(xa, y), (xb, y)], fill=BLUE, width=3)
        for x in (xa, xb): d.line([(x, y - 12), (x, y + 12)], fill=BLUE, width=3)
        t(((xa + xb) / 2, y - 22 if above else y + 24), f"{round(v * 1000)}", fnt(sz, True), BLUE)
    def vdim(x, ya, yb, v, left=True, sz=28):
        d.line([(x, ya), (x, yb)], fill=BLUE, width=3)
        for y in (ya, yb): d.line([(x - 12, y), (x + 12, y)], fill=BLUE, width=3)
        t((x - 28 if left else x + 28, (ya + yb) / 2), f"{round(v * 1000)}", fnt(sz, True), BLUE, rot=90)

    t((120, 100), p["title"], fnt(46, True), INK, "lm")
    t((120, 165), f"* Total Length = {total:g} m  ({' + '.join(f'{f['len']:g}' for f in fa)})", fnt(32), INK, "lm")
    t((120, 210), f"* Height = {H:g} m" + ("  (external)" if p.get("external") else ""), fnt(32), INK, "lm")

    # PLAN: hoarding wraps the left side, the front (bottom) and the right side of the building; returns go back to the lease line
    sp = min(800 / (fr + 0.4), 900 / (max(ls, rs) + 2.4))
    ox, oy = 200, 1180                      # bottom-left outer corner
    P = lambda x, y: (ox + x * sp, oy - y * sp)
    t((120, 300), "PLAN", fnt(28, True), INK, "lm")
    gap = 1.6                               # front gap to the building: not measured, drawn only
    top = max(ls, rs)
    d.rectangle([P(lr, top + 1.6), P(fr - rr, gap)], outline=RED, width=4)   # lease line = the building
    t(((P(lr, 0)[0] + P(fr - rr, 0)[0]) / 2, (P(0, top + 1.6)[1] + P(0, gap)[1]) / 2), "LEASE LINE", fnt(30, True), RED)
    d.line([P(lr, ls), P(0, ls), P(0, 0), P(fr, 0), P(fr, rs), P(fr - rr, rs)], fill=INK, width=5, joint="curve")
    # entry on the right side, doors swing in
    ey0, ey1 = P(0, doff)[1], P(0, doff + dw)[1]; xr = P(fr, 0)[0]; half = (ey0 - ey1) / 2
    d.line([(xr, ey0 - 3), (xr, ey1 + 3)], fill=(252, 252, 250), width=8)
    d.line([(xr, ey0), (xr - half, ey0)], fill=INK, width=3); d.line([(xr, ey1), (xr - half, ey1)], fill=INK, width=3)
    d.arc([xr - half, ey0 - half, xr + half, ey0 + half], 180, 270, fill=INK, width=2)
    d.arc([xr - half, ey1 - half, xr + half, ey1 + half], 90, 180, fill=INK, width=2)
    hdim(P(0, 0)[0], P(lr, 0)[0], P(0, ls)[1] - 30, lr, sz=24)
    hdim(P(fr - rr, 0)[0], P(fr, 0)[0], P(0, rs)[1] - 30, rr, sz=24)
    vdim(P(0, 0)[0] - 40, P(0, ls)[1], oy, ls)
    vdim(xr + 45, oy, ey0, doff, left=False, sz=24); vdim(xr + 45, ey0, ey1, dw, left=False, sz=24)
    vdim(xr + 45, ey1, P(0, rs)[1], rs - doff - dw, left=False, sz=24)
    vdim(xr + 115, oy, P(0, rs)[1], rs, left=False)
    hdim(P(0, 0)[0], xr, oy + 60, fr, above=False)

    # ELEVATION (faces unfolded)
    se = min(1060 / total, 600 / H)
    ex = 1240; eyb = 900; eyt = eyb - H * se
    xs = [ex]
    for f in fa: xs.append(xs[-1] + f["len"] * se)
    t((ex, eyt - 160), "ELEVATION (faces unfolded)", fnt(28, True), INK, "lm")
    d.rectangle([xs[0], eyt, xs[-1], eyb], outline=INK, width=5)
    for x in xs[1:-1]: d.line([(x, eyt), (x, eyb)], fill=INK, width=3)
    dx0, dx1, dyt = xs[3] + doff * se, xs[3] + (doff + dw) * se, eyb - dh * se
    d.rectangle([dx0, dyt, dx1, eyb], outline=INK, width=4)
    d.line([(dx0, dyt), (dx1, eyb)], fill=INK, width=3); d.line([(dx1, dyt), (dx0, eyb)], fill=INK, width=3)
    hdim(xs[0], xs[-1], eyt - 85, total)
    vdim(xs[-1] + 45, eyt, eyb, H, left=False)
    names = ["return", "left side", "front", "right side", "return"]
    for i, f in enumerate(fa):
        hdim(xs[i], xs[i + 1], eyb + 55, f["len"], above=False, sz=24 if f["len"] * se < 80 else 28)
        t(((xs[i] + xs[i + 1]) / 2, eyb + 125), names[i], fnt(20), GREY)
    ym = eyb - min(dh, H) * se / 2
    hdim(xs[3], dx0, ym, doff, sz=22); hdim(dx0, dx1, eyt - 25, dw, sz=22); hdim(dx1, xs[4], ym, rs - doff - dw, sz=22)
    im.save(out)

if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2])
