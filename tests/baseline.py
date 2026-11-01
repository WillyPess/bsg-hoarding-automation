"""Baseline references for the drawings and documents of the reference jobs.

The lite handoff has no reference PDFs or PNGs, so the outputs that were checked by eye on 2026-11-01
are pinned here instead: a hash of the pixels of every PNG and the extracted text of every PDF page.
They live in expected/<Job>/baseline.json. Any change to a drawing or document fails the tests until
the new outputs are checked and the baseline is updated with tests/update_baseline.py.

PNG hashes depend on the pinned Pillow version and the DejaVu fonts in fonts/; PDF text on reportlab,
pypdf and LibreOffice (the materials PDF).
"""
import hashlib, json, os, shutil, sys

from PIL import Image

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
