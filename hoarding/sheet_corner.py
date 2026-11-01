"""Corner-shop hoarding sheet in the boss's grid-paper layout: L-shaped plan (left) + unfolded elevation (right), mm.
Usage: sheet_corner.py job.json out.png   (job.json with "faces": angled return, side, front with door_offset, right return)"""
import sys, json, math
from PIL import Image, ImageDraw, ImageFont
from paths import F, FB
fnt = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
INK, BLUE, RED, GREY = (20, 22, 26), (30, 60, 170), (190, 30, 60), (110, 115, 120)

def render(p, out):
    fa = p["faces"]; ang, side, front, rr = fa[0]["len"], fa[1]["len"], fa[2]["len"], fa[3]["len"]
    doff, dw, dh, H = fa[2]["door_offset"], p["door_width"], p["door_height"], p["height"]
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
    t((120, 210), f"* Height = {H:g} m", fnt(32), INK, "lm")
    t((120, 255), "* Corner shop: two faces, plus an angled return by the lift", fnt(26), GREY, "lm")

    # PLAN: outer corner bottom-left, side face up, front face to the right
    a = ang / math.sqrt(2)                       # angled return drawn at 45 deg (angle not critical)
    sp = min(760 / (front + 0.8), 1000 / (side + a + 1.2))
    ox, oy = 250, 1400
    P = lambda x, y: (ox + x * sp, oy - y * sp)
    t((120, 320), "PLAN", fnt(28, True), INK, "lm")
    # lease line (shop), dashed red: up the shop side, round the shop corner, along the shop front
    lease = [P(a, side + a), P(a, rr), P(front, rr)]
    for (x0, y0), (x1, y1) in zip(lease, lease[1:]):
        n = int(math.hypot(x1 - x0, y1 - y0) // 22)
        for i in range(n):
            if i % 2 == 0: d.line([(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n), (x0 + (x1 - x0) * (i + 1) / n, y0 + (y1 - y0) * (i + 1) / n)], fill=RED, width=4)
    t(((P(a, 0)[0] + P(front, 0)[0]) / 2, P(0, rr)[1] - 24), "lease line", fnt(22), RED)
    t((P(a, 0)[0] + 24, (P(0, rr)[1] + P(0, side)[1]) / 2), "lease line", fnt(22), RED, rot=90)
    t(((P(a, 0)[0] + P(front, 0)[0]) / 2, (P(0, rr)[1] + P(0, side)[1]) / 2), "SHRUNGAAR", fnt(30, True), GREY)
    # hoarding
    d.line([P(a, side + a), P(0, side), P(0, 0), P(front, 0), P(front, rr)], fill=INK, width=5, joint="curve")
    # lift on the wall at the far end of the side face
    lx0, ly = P(-1.9, side + a + 0.7), P(-0.2, side + a + 0.1)
    d.rectangle([lx0[0], lx0[1], ly[0], ly[1]], outline=GREY, width=3); t(((lx0[0] + ly[0]) / 2, (lx0[1] + ly[1]) / 2), "LIFT", fnt(22, True), GREY)
    t((P(0, side + a)[0] + 40, P(0, side + a)[1] - 60), f"{round(ang * 1000)} angled return:", fnt(22, True), RED, "lm")
    t((P(0, side + a)[0] + 40, P(0, side + a)[1] - 32), "keep clear of the lift (angle to suit)", fnt(22, True), RED, "lm")
    # entry in the front, swinging in
    ex0, ex1 = P(doff, 0)[0], P(doff + dw, 0)[0]; yb = oy; half = (ex1 - ex0) / 2
    d.line([(ex0 + 3, yb), (ex1 - 3, yb)], fill=(252, 252, 250), width=8)
    d.line([(ex0, yb), (ex0, yb - half)], fill=INK, width=3); d.line([(ex1, yb), (ex1, yb - half)], fill=INK, width=3)
    d.arc([ex0 - half, yb - half, ex0 + half, yb + half], 270, 360, fill=INK, width=2)
    d.arc([ex1 - half, yb - half, ex1 + half, yb + half], 180, 270, fill=INK, width=2)
    vdim(P(0, 0)[0] - 40, P(0, side)[1], oy, side)
    vdim(P(front, 0)[0] + 40, P(0, rr)[1], oy, rr, left=False)
    hdim(P(0, 0)[0], ex0, oy + 45, doff, above=False, sz=24); hdim(ex0, ex1, oy + 45, dw, above=False, sz=24)
    hdim(ex1, P(front, 0)[0], oy + 45, front - doff - dw, above=False, sz=24)
    hdim(P(0, 0)[0], P(front, 0)[0], oy + 110, front, above=False)

    # ELEVATION (faces unfolded)
    se = min(1180 / total, 700 / H)
    ex = 1110; eyb = 1150; eyt = eyb - H * se
    xs = [ex]
    for f in fa: xs.append(xs[-1] + f["len"] * se)
    t((ex, eyt - 100), "ELEVATION (faces unfolded)", fnt(28, True), INK, "lm")
    d.rectangle([xs[0], eyt, xs[-1], eyb], outline=INK, width=5)
    for x in xs[1:-1]: d.line([(x, eyt), (x, eyb)], fill=INK, width=3)
    dx0, dx1, dyt = xs[2] + doff * se, xs[2] + (doff + dw) * se, eyb - dh * se
    d.rectangle([dx0, dyt, dx1, eyb], outline=INK, width=4)
    d.line([(dx0, dyt), (dx1, eyb)], fill=INK, width=3); d.line([(dx1, dyt), (dx0, eyb)], fill=INK, width=3)
    hdim(xs[0], xs[-1], eyt - 30, total)
    vdim(xs[-1] + 45, eyt, eyb, H, left=False)
    names = ["angled\nreturn", "side", "front", "return"]
    for i, f in enumerate(fa):
        hdim(xs[i], xs[i + 1], eyb + 55, f["len"], above=False, sz=24 if f["len"] * se < 80 else 28)
        t(((xs[i] + xs[i + 1]) / 2, eyb + 125), names[i] if i < 4 else f["name"], fnt(20), GREY)
    t((xs[2], eyb + 165), "CORNER", fnt(20, True), GREY); d.line([(xs[2], eyb + 80), (xs[2], eyb + 150)], fill=GREY, width=2)
    hdim(dx0, dx1, dyt - 28, dw, sz=22)
    hdim(xs[2], dx0, eyb - dh * se / 2, doff, sz=22)            # mid-height of the entry (boss, 2026-10-20)
    hdim(dx1, xs[3], eyb - dh * se / 2, front - doff - dw, sz=22)
    im.save(out)

if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2])
