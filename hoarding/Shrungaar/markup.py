"""Shrungaar photo markup: Gus's hoarding limit, entry placed in perspective 2200-3800 from the corner on the 8600 front."""
from PIL import Image, ImageDraw, ImageFont
import os
D = os.path.dirname(os.path.abspath(__file__))
im = Image.open(f"{D}/Shrungaar_photo.png").convert("RGB"); d = ImageDraw.Draw(im)
RED, W = (225, 20, 20), 6
A, B, C, Dp, E = (605, 980), (545, 1042), (690, 1466), (1825, 1118), (1680, 1080)   # read off Gus's sketch
d.line([A, B, C, Dp, E], fill=RED, width=W, joint="curve")
F, s0, s1, r = 8.6, 2.2, 3.8, 2.0          # r = far/near depth along the front (from the shop's corner vs end heights)
def at(m):
    s = m / F; f = s * r / (1 + s * (r - 1))
    x, y = C[0] + f * (Dp[0] - C[0]), C[1] + f * (Dp[1] - C[1])
    h = 445 * 1.261 / (1 + s)              # 2.4 m entry height, scaled from Gus's box
    return (x, y), (x, y - h)
(b0, t0), (b1, t1) = at(s0), at(s1)
d.line([b0, t0, t1, b1], fill=RED, width=W); d.line([t0, b1], fill=RED, width=W); d.line([t1, b0], fill=RED, width=W)
ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
d.text((440, 900), "angled return:\nkeep clear of lift", font=ft, fill=RED, anchor="mm", align="center")
im.save(f"{D}/Shrungaar_hoarding_markup.jpg", quality=90)
