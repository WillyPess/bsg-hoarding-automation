"""Medibank Pacific Fair: plan showing the track + timber section on the left return (beside the fire door)."""
from PIL import Image, ImageDraw, ImageFont
import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))   # hoarding/ (run_job.py also sets PYTHONPATH)
from paths import F, FB
fnt = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
INK, BLUE, RED, GREEN, AMBER, GREY, WOOD = (20, 22, 26), (30, 60, 170), (190, 30, 60), (20, 140, 60), (205, 110, 0), (120, 120, 120), (150, 100, 40)
LR, FRONT, RR, STEP, PUSH = 3000, 7200, 1600, 1400, 300   # mm; STEP = lease line in front of the fire door wall; PUSH = left return pushed left of the shop (estimate)
TRACK = STEP                                              # track section: fire door wall to the shopfront line
W, Hc, G = 2400, 1500, 40
im = Image.new("RGB", (W, Hc), (252, 252, 250)); d = ImageDraw.Draw(im)
for x in range(0, W, G): d.line([(x, 0), (x, Hc)], fill=(196, 214, 232) if x % (G * 5) else (160, 186, 214))
for y in range(0, Hc, G): d.line([(0, y), (W, y)], fill=(196, 214, 232) if y % (G * 5) else (160, 186, 214))
t = lambda xy, s, f, c=INK, a="mm": d.text(xy, s, font=f, fill=c, anchor=a)
s = 0.17                      # px per mm
x0, y0 = 520, 300             # x0: left edge of the shop, y0: fire door wall line
X = lambda mm: x0 + mm * s; Y = lambda mm: y0 + mm * s
def upright(px, py): d.rectangle([px - 14, py - 14, px + 14, py + 14], fill=BLUE)
def vdim(x, a, b, v, col=BLUE):
    d.line([(x, a), (x, b)], fill=col, width=3)
    for y in (a, b): d.line([(x - 14, y), (x + 14, y)], fill=col, width=3)
    box = Image.new("RGBA", (160, 50), (0, 0, 0, 0)); ImageDraw.Draw(box).text((80, 25), str(v), font=fnt(30, True), fill=col, anchor="mm")
    box = box.rotate(90, expand=True); im.paste(box, (int(x - 60), int((a + b) / 2 - 80)), box)
def hdim(a, b, y, v, col=BLUE):
    d.line([(a, y), (b, y)], fill=col, width=3)
    for x in (a, b): d.line([(x, y - 14), (x, y + 14)], fill=col, width=3)
    t(((a + b) / 2, y + 28), str(v), fnt(30, True), col)

t((120, 80), "Medibank - Pacific Fair   |   PLAN (track section, for checking)", fnt(42, True), INK, "lm")
t((120, 140), f"* Height 4200 = 3600 sheet + 600 top     * Length {LR} + {FRONT + PUSH} + {RR} = {(LR + FRONT + PUSH + RR) / 1000:g} m", fnt(30), INK, "lm")
# fire door wall + fire door (opens out into the mall)
d.line([(X(-2200), Y(0)), (X(0), Y(0))], fill=GREY, width=6)
fx0, fx1 = X(-1900), X(-1000)
d.rectangle([fx0, Y(0) - 10, fx1, Y(0) + 4], fill=GREY)
d.arc([fx0 - 900 * s, Y(0) - 900 * s, fx0 + 900 * s, Y(0) + 900 * s], 0, 90, fill=GREY, width=2); d.line([(fx0, Y(0)), (fx0, Y(900))], fill=GREY, width=2)
t(((fx0 + fx1) / 2, Y(0) - 30), "FIRE DOOR", fnt(24, True), GREY)
# shop: side wall from the fire door wall out to the shopfront, then the lease line
d.line([(X(0), Y(0)), (X(0), Y(STEP))], fill=GREY, width=6)
for x in range(int(X(0)), int(X(FRONT)), 22): d.line([(x, Y(STEP)), (x + 11, Y(STEP))], fill=RED, width=4)
t((X(FRONT / 2), Y(STEP) - 28), "lease line (shopfront)", fnt(24), RED)
# hoarding: left return (pushed PUSH left of the shop), straight front, right return
A, B, C, D = (X(-PUSH), Y(0)), (X(-PUSH), Y(LR)), (X(FRONT), Y(LR)), (X(FRONT), Y(STEP))
d.line([(X(-PUSH), Y(TRACK)), B, C, D], fill=INK, width=5)
for dx in (-7, 7): d.line([(A[0] + dx, Y(0)), (A[0] + dx, Y(TRACK))], fill=GREEN, width=4)
for mm in range(0, TRACK, 600): d.rectangle([A[0] - 12, Y(mm) - 6, A[0] + 12, Y(mm) + 6], fill=WOOD)
# uprights at the joins between sheets, none in the corners (Gus, 2026-11-01): 2400 from the wall on the left return,
# 1100 / 2300 / 3500 / 4700 / 6300 from the left corner along the front, 400 from the front corner on the right return
upright(A[0], Y(2400)); t((A[0] + 130, Y(2400)), "upright at the sheet join (2400 from the wall)", fnt(22, True), BLUE, "lm")
t((B[0] - 30, B[1] + 34), "no upright at corners", fnt(22, True), BLUE, "rm")
for m in (1100, 2300, 3500, 4700, 6300): upright(X(-PUSH + m), C[1])
upright(D[0], Y(LR - 400))
# dims
vdim(A[0] + 70, Y(0), Y(TRACK), TRACK, GREEN)
vdim(A[0] + 70, Y(TRACK), Y(LR), LR - TRACK)
vdim(X(-2600), Y(0), Y(LR), LR)
vdim(X(FRONT) + 60, Y(STEP), Y(LR), RR)
hdim(X(0), X(FRONT), Y(LR) + 70, f"{FRONT} (shopfront)")
hdim(X(-PUSH), X(0), Y(LR) + 70, f"{PUSH}?", AMBER)
t((X(FRONT / 2), Y(LR) - 30), "front hoarding (straight, parallel to the shopfront)", fnt(24), INK)
# legend + notes
ly = 1250
d.line([(120, ly), (200, ly)], fill=GREEN, width=8); t((220, ly), "TRACK + TIMBERS (90mm track top + bottom, 90x45 MGP10 at 600 centres), no uprights", fnt(26), INK, "lm")
d.rectangle([146, ly + 46, 174, ly + 74], fill=BLUE); t((220, ly + 60), "upright + 6 counterweights", fnt(26), INK, "lm")
t((120, ly + 115), f"? in orange: how far the left return is pushed past the shop is a guess ({PUSH}), please confirm", fnt(26, True), AMBER, "lm")
t((120, ly + 160), "Note: track + timbers is a suggestion only; BSG is still learning this method.", fnt(26, True), AMBER, "lm")
im.save("Medibank_track_plan_CHECK.png")
