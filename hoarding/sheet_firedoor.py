"""Grid sheet for a fire-door job (boss's style, mm): plan with the stepped lease line + track section, unfolded elevation.
Usage: sheet_firedoor.py <Job>/job.json out.png   (job.json: faces, height, door_offset, door_width, shopfront, step, push, right_return, track)"""
import sys, json
from PIL import Image, ImageDraw, ImageFont
from paths import F, FB
fnt = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
INK, BLUE, RED, GREEN, AMBER, GREY, WOOD = (20, 22, 26), (30, 60, 170), (190, 30, 60), (20, 140, 60), (205, 110, 0), (120, 120, 120), (150, 100, 40)
J = json.load(open(sys.argv[1])); k = lambda v: round(v * 1000)
LR, FRONT, RR = (k(f["len"]) for f in J["faces"])
SHOP, STEP, PUSH, TRACK, H = k(J["shopfront"]), k(J["step"]), k(J["push"]), k(J["track"]["len"]), k(J["height"])
DO, DW, DH = k(J["door_offset"]), k(J["door_width"]), k(J.get("door_height", 2.4))
W, Hc, G = 2600, 1700, 40
im = Image.new("RGB", (W, Hc), (252, 252, 250)); d = ImageDraw.Draw(im)
for x in range(0, W, G): d.line([(x, 0), (x, Hc)], fill=(196, 214, 232) if x % (G * 5) else (160, 186, 214))
for y in range(0, Hc, G): d.line([(0, y), (W, y)], fill=(196, 214, 232) if y % (G * 5) else (160, 186, 214))
def t(xy, s, f, c=INK, a="mm", rot=0):
    if not rot: d.text(xy, s, font=f, fill=c, anchor=a); return
    box = Image.new("RGBA", (220, 50), (0, 0, 0, 0)); ImageDraw.Draw(box).text((110, 25), s, font=f, fill=c, anchor="mm")
    box = box.rotate(rot, expand=True); im.paste(box, (int(xy[0] - box.width / 2), int(xy[1] - box.height / 2)), box)
def vdim(x, a, b, v, col=BLUE, left=True):
    d.line([(x, a), (x, b)], fill=col, width=3)
    for y in (a, b): d.line([(x - 12, y), (x + 12, y)], fill=col, width=3)
    t((x - 24 if left else x + 24, (a + b) / 2), str(v), fnt(26, True), col, rot=90)
def hdim(a, b, y, v, col=BLUE, above=False):
    d.line([(a, y), (b, y)], fill=col, width=3)
    for x in (a, b): d.line([(x, y - 12), (x, y + 12)], fill=col, width=3)
    t(((a + b) / 2, y - 22 if above else y + 24), str(v), fnt(26, True), col)
L = LR + FRONT + RR
t((100, 90), J["title"], fnt(46, True), INK, "lm")
t((100, 160), f"* Total Length = {L / 1000:g} m ({LR} + {FRONT} + {RR})", fnt(34), INK, "lm")
t((100, 210), f"* Height = {H / 1000:g} m", fnt(34), INK, "lm")

# PLAN (left)
s = 0.1; x0, y0 = 400, 420                       # x0: shop's left side, y0: fire door wall
X = lambda mm: x0 + mm * s; Y = lambda mm: y0 + mm * s
t((100, 340), "PLAN", fnt(28, True), INK, "lm")
d.line([(X(-2300), Y(0)), (X(0), Y(0))], fill=GREY, width=5)
fx0, fx1 = X(-2000), X(-1100)
d.rectangle([fx0, Y(0) - 8, fx1, Y(0) + 3], fill=GREY)
d.arc([fx0 - 900 * s, Y(0) - 900 * s, fx0 + 900 * s, Y(0) + 900 * s], 0, 90, fill=GREY, width=2); d.line([(fx0, Y(0)), (fx0, Y(900))], fill=GREY, width=2)
t(((fx0 + fx1) / 2, Y(0) - 24), "FIRE DOOR", fnt(20, True), GREY)
d.line([(X(0), Y(0)), (X(0), Y(STEP))], fill=GREY, width=5)
for x in range(int(X(0)), int(X(SHOP)), 18): d.line([(x, Y(STEP)), (x + 9, Y(STEP))], fill=RED, width=4)
t((X(SHOP / 2), Y(STEP) - 22), "lease line", fnt(22), RED)
A, B, C, D = (X(-PUSH), Y(0)), (X(-PUSH), Y(LR)), (X(SHOP), Y(LR)), (X(SHOP), Y(STEP))
d.line([(A[0], Y(TRACK)), B, C, D], fill=INK, width=5)
for dx in (-5, 5): d.line([(A[0] + dx, Y(0)), (A[0] + dx, Y(TRACK))], fill=GREEN, width=3)
ex0, ex1 = X(DO - PUSH), X(DO - PUSH + DW); half = (ex1 - ex0) / 2; pyf = Y(LR)
d.line([(ex0 + 3, pyf), (ex1 - 3, pyf)], fill=(252, 252, 250), width=8)
d.line([(ex0, pyf), (ex0, pyf - half)], fill=INK, width=3); d.line([(ex1, pyf), (ex1, pyf - half)], fill=INK, width=3)
d.arc([ex0 - half, pyf - half, ex0 + half, pyf + half], 270, 360, fill=INK, width=2)
d.arc([ex1 - half, pyf - half, ex1 + half, pyf + half], 180, 270, fill=INK, width=2)
t((A[0] - 18, Y(TRACK * 0.8)), "track +\ntimbers", fnt(20, True), GREEN, "rm")
vdim(A[0] + 90, Y(0), Y(TRACK), TRACK, GREEN, left=False); vdim(A[0] + 90, Y(TRACK), Y(LR), LR - TRACK, left=False)
vdim(X(-2450), Y(0), Y(LR), LR)
vdim(X(SHOP) + 45, Y(STEP), Y(LR), RR, left=False)
hdim(A[0], ex0, pyf + 50, DO); hdim(ex0, ex1, pyf + 50, DW); hdim(ex1, X(SHOP), pyf + 50, FRONT - DO - DW)
hdim(A[0], X(SHOP), pyf + 125, FRONT)
yp = Y(STEP) + 40; d.line([(A[0], yp), (X(0), yp)], fill=BLUE, width=3); [d.line([(x, yp - 10), (x, yp + 10)], fill=BLUE, width=3) for x in (A[0], X(0))]
d.line([(X(0), Y(STEP)), (X(0), yp + 10)], fill=BLUE, width=1); t((A[0] - 12, yp), str(PUSH), fnt(26, True), BLUE, "rm")

# ELEVATION (right)
se = min(1250 / L, 900 / H); ex = 1220; eyb = 1400; eyt = eyb - H * se
xs = [ex, ex + LR * se, ex + (LR + FRONT) * se, ex + L * se]
t((ex, eyt - 100), "ELEVATION (returns unfolded)", fnt(28, True), INK, "lm")
d.rectangle([xs[0], eyt, xs[0] + TRACK * se, eyb], fill=(214, 238, 220))
d.rectangle([xs[0], eyt, xs[3], eyb], outline=INK, width=5)
for x in xs[1:3]: d.line([(x, eyt), (x, eyb)], fill=INK, width=3)
t((xs[0] + TRACK * se / 2, (eyt + eyb) / 2), "track +\ntimbers", fnt(20, True), GREEN)
dx0, dx1, dyt = xs[1] + DO * se, xs[1] + (DO + DW) * se, eyb - DH * se
d.rectangle([dx0, dyt, dx1, eyb], outline=INK, width=4)
d.line([(dx0, dyt), (dx1, eyb)], fill=INK, width=3); d.line([(dx1, dyt), (dx0, eyb)], fill=INK, width=3)
hdim(xs[0], xs[3], eyt - 30, L, above=True)
vdim(xs[3] + 45, eyt, eyb, H, left=False)
for a, b, v in [(xs[0], xs[1], LR), (xs[1], xs[2], FRONT), (xs[2], xs[3], RR)]: hdim(a, b, eyb + 50, v)
hdim(dx0, dx1, dyt - 28, DW, above=True)
hdim(xs[1], dx0, eyb - DH * se / 2, DO, above=True)          # mid-height of the entry (boss, 2026-10-20)
hdim(dx1, xs[2], eyb - DH * se / 2, FRONT - DO - DW, above=True)
t((100, Hc - 110), "Track + timbers (90 mm track top + bottom, 90x45 MGP10 at 600 centres) in the first "
  f"{TRACK} of the left return, beside the fire door.", fnt(26), INK, "lm")
t((100, Hc - 60), "Note: track + timbers is a suggestion only; BSG is still learning this method.", fnt(26, True), AMBER, "lm")
im.save(sys.argv[2])
