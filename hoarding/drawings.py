"""Hoarding plan + unfolded elevation in BSG's hand-drawn layout. Sizes in metres."""
import sys, json, math
from PIL import Image, ImageDraw, ImageFont

from paths import F, FB
font = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
INK, RED, GREY, AMBER = (25, 28, 32), (215, 25, 28), (110, 116, 122), (200, 110, 0)

def fmt(v): return f"{v:.2f}".rstrip("0").rstrip(".") + " m"

def render(p, out):
    front, ret, H = p["front"], p["return"], p["height"]
    doff, dw, dh = p["door_offset"], p["door_width"], p["door_height"]
    est = set(p.get("estimated", []))
    W, Hc = 1800, 2250
    im = Image.new("RGB", (W, Hc), "white"); d = ImageDraw.Draw(im)
    def col(k): return AMBER if k in est else INK
    def text(xy, s, f, fill=INK, anchor="mm"): d.text(xy, s, font=f, fill=fill, anchor=anchor)
    def dim(a, b, label, key=None, off=0, vertical=False):
        c = col(key); f = font(30, True)
        (x1, y1), (x2, y2) = a, b
        d.line([a, b], fill=c, width=3)
        for (x, y) in (a, b):
            if vertical: d.line([(x - 14, y), (x + 14, y)], fill=c, width=3)
            else: d.line([(x, y - 14), (x, y + 14)], fill=c, width=3)
            d.line([(x - 9, y + 9), (x + 9, y - 9)], fill=c, width=3)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if not label: return
        lab = label + (" *" if key in est else "")
        if vertical: text((mx - 18, my), lab, f, c, "rm")
        else: text((mx, my - 26 - off), lab, f, c)

    # header
    text((90, 90), p["title"], font(52, True), INK, "lm")
    text((90, 160), f"H: {fmt(H)}" + (" *" if "height" in est else ""), font(40), col("height"), "lm")
    text((90, 215), f"Length: {fmt(front + 2 * ret)}  ({fmt(ret)} + {fmt(front)} + {fmt(ret)})", font(40), INK, "lm")

    # ---------- PLAN ----------
    text((90, 330), "PLAN", font(30, True), GREY, "lm")
    s = min(1300 / front, 420 / ret)          # px per metre
    x0 = (W - front * s) / 2; y0 = 520        # lease line y
    x1 = x0 + front * s; yf = y0 + ret * s
    text(((x0 + x1) / 2, 400), "LEASE LINE (SHOPFRONT, NO ACCESS)", font(32, True), RED)
    # hatch behind lease line
    for x in range(int(x0), int(x1), 34): d.line([(x, y0 - 4), (x + 30, y0 - 46)], fill=RED, width=3)
    # shop entry on lease line
    ex0, ex1 = x0 + doff * s, x0 + (doff + dw) * s
    d.rectangle([ex0, y0 - 60, ex1, y0], fill="white", outline=RED, width=4)
    text(((ex0 + ex1) / 2, y0 - 30), "SHOP ENTRY", font(26, True), RED)
    d.line([(x0, y0), (x1, y0)], fill=RED, width=5)
    # hoarding limit: returns + front
    d.line([(x0, y0), (x0, yf), (x1, yf), (x1, y0)], fill=INK, width=7, joint="curve")
    # hoarding entry: double doors opening outwards (into the mall)
    d.line([(ex0, yf), (ex1, yf)], fill="white", width=9)
    half = dw * s / 2
    for hx, sgn in ((ex0, 1), (ex1, -1)):
        d.line([(hx, yf), (hx, yf - half)], fill=INK, width=4)
        box = [hx - half, yf - half, hx + half, yf + half]
        if sgn > 0: d.arc(box, 270, 360, fill=INK, width=2)
        else: d.arc(box, 180, 270, fill=INK, width=2)
    for hx in (ex0, ex1): d.line([(hx - 2, yf - 10), (hx - 2, yf + 10)], fill=INK, width=4)
    text(((ex0 + ex1) / 2, yf + 34), "HOARDING ENTRY", font(26, True), INK)
    # dims
    dim((x0 - 70, y0), (x0 - 70, yf), fmt(ret), "return", vertical=True)
    d.line([(x1 + 70, y0), (x1 + 70, yf)], fill=col("return"), width=3)
    for y in (y0, yf): d.line([(x1 + 56, y), (x1 + 84, y)], fill=col("return"), width=3)
    text((x1 + 92, (y0 + yf) / 2), fmt(ret) + (" *" if "return" in est else ""), font(30, True), col("return"), "lm")
    yd = yf + 130
    dim((x0, yd), (ex0, yd), fmt(doff), "door_offset")
    dim((ex0, yd), (ex1, yd), fmt(dw), "door_width")
    dim((ex1, yd), (x1, yd), fmt(front - doff - dw), "front")
    dim((x0, yd + 90), (x1, yd + 90), fmt(front), "front")

    # ---------- ELEVATION (unfolded) ----------
    ytop_label = yd + 210
    text((90, ytop_label), "ELEVATION (RETURNS UNFOLDED)", font(30, True), GREY, "lm")
    total = front + 2 * ret
    se = min(1340 / total, 820 / H)
    X0 = (W - total * se) / 2; Yb = ytop_label + 90 + H * se; Yt = Yb - H * se
    xs = [X0, X0 + ret * se, X0 + (ret + front) * se, X0 + total * se]
    d.rectangle([xs[0], Yt, xs[3], Yb], outline=INK, width=6)
    for x in xs[1:3]: d.line([(x, Yt), (x, Yb)], fill=INK, width=4)
    text(((xs[0] + xs[1]) / 2, (Yt + Yb) / 2), "RETURN", font(26, True), GREY)
    text(((xs[2] + xs[3]) / 2, (Yt + Yb) / 2), "RETURN", font(26, True), GREY)
    text(((xs[1] + xs[2]) / 2, Yt + 50), "FRONT", font(26, True), GREY)
    dx0, dx1 = xs[1] + doff * se, xs[1] + (doff + dw) * se
    d.rectangle([dx0, Yb - dh * se, dx1, Yb], outline=INK, width=5)
    d.line([((dx0 + dx1) / 2, Yb - dh * se), ((dx0 + dx1) / 2, Yb)], fill=INK, width=3)
    text(((dx0 + dx1) / 2, Yb - dh * se - 26), "ENTRY", font(24, True), INK)
    # height dims
    dim((xs[3] + 60, Yt), (xs[3] + 60, Yb), "", "height", vertical=True)
    text((xs[3] + 80, (Yt + Yb) / 2), fmt(H) + (" *" if "height" in est else ""), font(30, True), col("height"), "lm")
    dim((dx1 + 40, Yb - dh * se), (dx1 + 40, Yb), "", "door_height", vertical=True)
    text((dx1 + 58, Yb - dh * se / 2), fmt(dh) + (" *" if "door_height" in est else ""), font(30, True), col("door_height"), "lm")
    yb = Yb + 70
    segs = [(xs[0], xs[1], ret, "return"), (xs[1], dx0, doff, "door_offset"), (dx0, dx1, dw, "door_width"),
            (dx1, xs[2], front - doff - dw, "front"), (xs[2], xs[3], ret, "return")]
    for a, b, v, k in segs: dim((a, yb), (b, yb), fmt(v), k)
    dim((xs[0], yb + 90), (xs[3], yb + 90), fmt(total), "front")
    if est:
        text((90, Hc - 70), "* Estimated from the photo. Confirm on site before ordering materials.", font(30, True), AMBER, "lm")
    im.save(out)

if __name__ == "__main__":
    render(json.loads(sys.argv[1]), sys.argv[2])
