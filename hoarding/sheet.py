"""Hoarding sheet in the boss's grid-paper layout: plan (left) + unfolded elevation (right), mm."""
import sys, json
from PIL import Image, ImageDraw, ImageFont
from paths import F, FB
fnt = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
INK, BLUE, RED, AMBER = (20, 22, 26), (30, 60, 170), (190, 30, 60), (205, 110, 0)

def render(p, out):
    front, ret, H = p["front"], p["return"], p["height"]
    doff, dw, dh = p["door_offset"], p["door_width"], p["door_height"]
    est = set(p.get("estimated", []))
    W, Hc, G = 2400, 1600, 40
    im = Image.new("RGB", (W, Hc), (252, 252, 250)); d = ImageDraw.Draw(im)
    for x in range(0, W, G): d.line([(x, 0), (x, Hc)], fill=(196, 214, 232) if x % (G * 5) else (160, 186, 214), width=1)
    for y in range(0, Hc, G): d.line([(0, y), (W, y)], fill=(196, 214, 232) if y % (G * 5) else (160, 186, 214), width=1)
    c = lambda k: AMBER if k in est else BLUE
    lab = lambda v, k: f"{int(round(v))}" + ("*" if k in est else "")
    def t(xy, s, f, fill, anchor="mm", rot=0):
        if not rot: d.text(xy, s, font=f, fill=fill, anchor=anchor); return
        box = d.textbbox((0, 0), s, font=f); tw, th = box[2] - box[0] + 8, box[3] - box[1] + 12
        tim = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); ImageDraw.Draw(tim).text((tw / 2, th / 2), s, font=f, fill=fill, anchor="mm")
        tim = tim.rotate(rot, expand=True); im.paste(tim, (int(xy[0] - tim.width / 2), int(xy[1] - tim.height / 2)), tim)
    def hdim(xa, xb, y, v, k, above=True):
        col = c(k); d.line([(xa, y), (xb, y)], fill=col, width=3)
        for x in (xa, xb): d.line([(x, y - 14), (x, y + 14)], fill=col, width=3)
        t(((xa + xb) / 2, y - 24 if above else y + 26), lab(v, k), fnt(30, True), col)
    def vdim(x, ya, yb, v, k, left=True):
        col = c(k); d.line([(x, ya), (x, yb)], fill=col, width=3)
        for y in (ya, yb): d.line([(x - 14, y), (x + 14, y)], fill=col, width=3)
        t((x - 30 if left else x + 30, (ya + yb) / 2), lab(v, k), fnt(30, True), col, rot=90)

    # notes
    t((120, 110), p["title"], fnt(46, True), INK, "lm")
    total = front + 2 * ret
    t((120, 180), f"* Total Length = {total/1000:g} m" + (" (est.)" if est & {"front", "return"} else ""), fnt(36), c("front") if est & {"front", "return"} else INK, "lm")
    t((120, 230), f"* Height = {H/1000:g} m" + (" (est.)" if "height" in est else ""), fnt(36), c("height") if "height" in est else INK, "lm")

    # PLAN (left)
    sp = min(560 / front, 230 / ret)
    px0, py0 = 140, 420
    px1, pyf = px0 + front * sp, py0 + ret * sp
    t((px0, 360), "PLAN", fnt(28, True), INK, "lm")
    for x in range(int(px0), int(px1), 22): d.line([(x, py0), (x + 11, py0)], fill=RED, width=4)   # lease line dashed
    t(((px0 + px1) / 2, py0 - 26), "lease line", fnt(24), RED)
    d.line([(px0, py0), (px0, pyf), (px1, pyf), (px1, py0)], fill=INK, width=5)
    ex0, ex1 = px0 + doff * sp, px0 + (doff + dw) * sp; half = (ex1 - ex0) / 2
    d.line([(ex0 + 3, pyf), (ex1 - 3, pyf)], fill=(252, 252, 250), width=8)
    d.line([(ex0, pyf), (ex0, pyf - half)], fill=INK, width=3); d.line([(ex1, pyf), (ex1, pyf - half)], fill=INK, width=3)
    d.arc([ex0 - half, pyf - half, ex0 + half, pyf + half], 270, 360, fill=INK, width=2)
    d.arc([ex1 - half, pyf - half, ex1 + half, pyf + half], 180, 270, fill=INK, width=2)
    vdim(px0 - 40, py0, pyf, ret, "return"); vdim(px1 + 40, py0, pyf, ret, "return", left=False)
    hdim(px0, ex0, pyf + 50, doff, "door_offset", above=False); hdim(ex0, ex1, pyf + 50, dw, "door_width", above=False)
    hdim(ex1, px1, pyf + 50, front - doff - dw, "front", above=False)
    hdim(px0, px1, pyf + 120, front, "front", above=False)

    # ELEVATION (right)
    se = min(1300 / total, 900 / H)
    ex = 960; eyb = 1380; eyt = eyb - H * se
    xs = [ex, ex + ret * se, ex + (ret + front) * se, ex + total * se]
    t((ex, eyt - 90), "ELEVATION (returns unfolded)", fnt(28, True), INK, "lm")
    d.rectangle([xs[0], eyt, xs[3], eyb], outline=INK, width=5)
    for x in xs[1:3]: d.line([(x, eyt), (x, eyb)], fill=INK, width=3)
    dx0, dx1, dyt = xs[1] + doff * se, xs[1] + (doff + dw) * se, eyb - dh * se
    d.rectangle([dx0, dyt, dx1, eyb], outline=INK, width=4)
    d.line([(dx0, dyt), (dx1, eyb)], fill=INK, width=3); d.line([(dx1, dyt), (dx0, eyb)], fill=INK, width=3)
    hdim(xs[0], xs[3], eyt - 30, H if False else total, "front")
    vdim(xs[3] + 50, eyt, eyb, H, "height", left=False)
    for a, b, v, k in [(xs[0], xs[1], ret, "return"), (xs[1], xs[2], front, "front"), (xs[2], xs[3], ret, "return")]:
        hdim(a, b, eyb + 60, v, k, above=False)
    hdim(dx0, dx1, dyt - 30, dw, "door_width")
    hdim(xs[1], dx0, eyb - dh * se / 2, doff, "door_offset")   # mid-height of the entry (boss, 2026-10-20)
    if p.get("show_door_height") or abs(dh - 2400) > 1: vdim(dx1 + 30, dyt, eyb, dh, "door_height", left=False)   # only when not the standard 2400 (Gus, 2026-10-21)
    if est: t((120, Hc - 60), "* in orange: estimated from the photo, confirm on site", fnt(30, True), AMBER, "lm")
    im.save(out)

if __name__ == "__main__":
    render(json.loads(sys.argv[1]), sys.argv[2])
