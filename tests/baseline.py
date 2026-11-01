"""Baseline references for the drawings and documents of the reference jobs.

The lite handoff has no reference PDFs or PNGs, so the outputs that were checked by eye on 2026-11-01
are pinned here instead: a hash of the pixels of every PNG and the extracted text of every PDF page.
They live in expected/<Job>/baseline.json. Any change to a drawing or document fails the tests until
the new outputs are checked and the baseline is updated with tests/update_baseline.py.

PNG hashes depend on the pinned Pillow version and the DejaVu fonts in fonts/; PDF text on reportlab,
pypdf and LibreOffice (the materials PDF).

Drawings across environments: text renders slightly differently on Windows and Linux, so an exact hash only
holds on the machine that made it. When expected/<Job>/png/ holds the approved PNGs, the drawings are compared
with a tolerance instead (drawing_diff); the hash is only used for jobs without stored PNGs.
"""
import hashlib, json, os, shutil, sys

from PIL import Image, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import run_job
from check_fixtures import pdf_text

JOBS = list(json.load(open(os.path.join(ROOT, "expected", "expected_counts.json")))["jobs"])


def path(job):
    return os.path.join(ROOT, "expected", job, "baseline.json")


def png_hash(p):
    """sha256 of the image size and RGB pixels (not the file bytes, which change with the zlib build)."""
    im = Image.open(p).convert("RGB")
    return hashlib.sha256(f"{im.size}".encode() + im.tobytes()).hexdigest()


# Tolerant drawing comparison. A pixel counts as changed when no pixel within RADIUS px of it in the baseline
# has every channel within CHANNEL_TOL: a glyph moved by 1 px or anti-aliased a bit differently is not a change,
# a line or text in another colour or another place is. The test fails when more than MAX_PCT % of the pixels changed.
# MAX_PCT is provisional until measured on the Windows baselines (see README, Tests).
RADIUS, CHANNEL_TOL, MAX_PCT = 1, 24, 0.02


def png_dir(job):
    return os.path.join(ROOT, "expected", job, "png")


def drawing_diff(base, new, mask_out=None):
    """(% of pixels changed with the tolerance above, % of pixels that differ at all). Different sizes = 100 %.
    mask_out: optional path for a copy of the new image with the changed pixels in magenta."""
    a, b = Image.open(base).convert("RGB"), Image.open(new).convert("RGB")
    if a.size != b.size:
        return 100.0, 100.0
    total = a.size[0] * a.size[1]

    def worst_channel(x, y):
        r, g, bl = ImageChops.difference(x, y).split()
        return ImageChops.lighter(ImageChops.lighter(r, g), bl)
    raw = worst_channel(a, b)
    best = None
    for dx in range(-RADIUS, RADIUS + 1):
        for dy in range(-RADIUS, RADIUS + 1):
            m = worst_channel(ImageChops.offset(a, dx, dy), b)
            best = m if best is None else ImageChops.darker(best, m)
    changed = best.point(lambda v: 255 if v > CHANNEL_TOL else 0)
    if mask_out:
        Image.composite(Image.new("RGB", b.size, (255, 0, 255)), b, changed).save(mask_out)
    return 100.0 * changed.histogram()[255] / total, 100.0 * (total - raw.histogram()[0]) / total


def snapshot(work):
    """{"png": {name: hash}, "pdf": {name: [page text, ...]}} for the outputs in a job folder after run_job.run()."""
    names = sorted(os.listdir(work))
    return {"png": {n: png_hash(os.path.join(work, n)) for n in names if n.endswith(".png") and not n.endswith("_photo.png")},
            "pdf": {n: pdf_text(os.path.join(work, n))[1] for n in names if n.endswith(".pdf") and not n.startswith(".")}}


def load(job):
    with open(path(job), encoding="utf-8") as f:
        return json.load(f)


def save(job, snap):
    with open(path(job), "w", encoding="utf-8", newline="\n") as f:
        json.dump(snap, f, indent=1, ensure_ascii=False)
        f.write("\n")


def run_into(job, work):
    """Copy hoarding/<job> (inputs) to a clean folder and run the full pipeline there."""
    if os.path.exists(work):
        shutil.rmtree(work)
    shutil.copytree(os.path.join(ROOT, "hoarding", job), work)
    return run_job.run(work)
