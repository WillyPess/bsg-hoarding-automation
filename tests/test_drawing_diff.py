"""The tolerant drawing comparison still catches real changes (step B check: one ink colour changed in sheet.py)
and ignores what only differs between machines (a glyph 1 px off, slightly different anti-aliasing)."""
import os

import pytest
from PIL import Image, ImageChops

import baseline

SHEET = os.path.join(baseline.png_dir("Bikini"), "Bikini_hoarding_sheet.png")
pytestmark = pytest.mark.skipif(not os.path.exists(SHEET), reason="no stored PNG baseline")


def recolour(src, out, old, new):
    im = Image.open(src).convert("RGB")
    px = im.load()
    n = 0
    for x in range(im.size[0]):
        for y in range(im.size[1]):
            if px[x, y] == old:
                px[x, y] = new; n += 1
    im.save(out)
    return n


def test_lease_line_colour_change_fails(tmp_path):
    # the dashed red lease line (sheet.py RED) turned green: only about 0.05 % of the pixels, must still fail
    out = str(tmp_path / "x.png")
    assert recolour(SHEET, out, (190, 30, 60), (30, 140, 60)) > 0
    pct, _ = baseline.drawing_diff(SHEET, out)
    assert pct > baseline.MAX_PCT


def test_ink_colour_change_fails(tmp_path):
    out = str(tmp_path / "x.png")
    assert recolour(SHEET, out, (20, 22, 26), (60, 22, 26)) > 0
    assert baseline.drawing_diff(SHEET, out)[0] > baseline.MAX_PCT


def test_one_pixel_shift_and_light_antialias_pass(tmp_path):
    im = Image.open(SHEET).convert("RGB")
    shifted = ImageChops.offset(im, 1, 0)
    shifted = Image.eval(shifted, lambda v: min(255, v + 10))   # every channel a little lighter
    out = str(tmp_path / "x.png"); shifted.save(out)
    pct, raw = baseline.drawing_diff(SHEET, out)
    assert pct <= baseline.MAX_PCT and raw > 50   # nearly every pixel differs, none counts as a change


def test_different_size_fails(tmp_path):
    out = str(tmp_path / "x.png")
    Image.open(SHEET).convert("RGB").crop((0, 0, 100, 100)).save(out)
    assert baseline.drawing_diff(SHEET, out) == (100.0, 100.0)
