#!/usr/bin/env python3
"""Regression check: run every reference job in a clean copy and compare with the fixtures.

Usage (from the bundle root):  python3 check_fixtures.py [Job ...]
For each job it
  1. copies hoarding/<Job>/ (inputs only) to a temp folder and runs run_job.py there,
  2. checks the key counts against expected/expected_counts.json (the approved numbers),
  3. checks every cell of the new materials xlsx against expected/<Job>/<P>_materials.xlsx,
  4. checks page count and text of the package, materials and quotation PDFs,
  5. checks the sheet / layout PNGs pixel by pixel.
Exit code 0 = all passed.
"""
import json, os, re, sys, tempfile, shutil, glob
from pathlib import Path
from PIL import Image, ImageChops
import openpyxl
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import run_job

EXP = json.loads(Path(os.path.join(ROOT, "expected", "expected_counts.json")).read_text(encoding="utf-8"))["jobs"]


def cells(p):
    ws = openpyxl.load_workbook(p).active
    return {(c.row, c.column): c.value for row in ws.iter_rows() for c in row if c.value is not None}


def pdf_text(p):
    r = PdfReader(p)
    # drop dates that change run to run? none do: job.json fixes date and quote_date
    return len(r.pages), [re.sub(r"\s+", " ", pg.extract_text() or "").strip() for pg in r.pages]


def check(job):
    fails = []
    src = os.path.join(ROOT, "hoarding", job)
    J = json.loads(Path(os.path.join(src, "job.json")).read_text(encoding="utf-8")); P = J["prefix"]
    work = os.path.join(tempfile.mkdtemp(), job); shutil.copytree(src, work)
    s = run_job.run(work)
    for k, v in EXP[job].items():
        if k.endswith("_note"): continue
        got = s.get(k)
        if v is None and got is None: continue
        if got != v: fails.append(f"{k}: expected {v}, got {got}")
    if os.path.exists(f"{ROOT}/expected/{job}/{P}_materials.xlsx"):
      e, g = cells(f"{ROOT}/expected/{job}/{P}_materials.xlsx"), cells(f"{work}/{P}_materials.xlsx")
      for key in sorted(set(e) | set(g)):
        if e.get(key) != g.get(key): fails.append(f"materials cell {key}: expected {e.get(key)!r}, got {g.get(key)!r}")
    pdfs = [f"{P}_Hoarding_Package.pdf", f"{P}_materials.pdf"]
    if J.get("site") == "Pacific Fair": pdfs.append(J.get("quote_file", f"{P}_Quotation.pdf"))
    for f in pdfs:
        if not os.path.exists(f"{ROOT}/expected/{job}/{f}"): continue   # lite bundle: no PDFs
        (n1, t1), (n2, t2) = pdf_text(f"{ROOT}/expected/{job}/{f}"), pdf_text(f"{work}/{f}")
        if n1 != n2: fails.append(f"{f}: {n1} pages expected, got {n2}")
        for i, (a, b) in enumerate(zip(t1, t2)):
            if a != b: fails.append(f"{f} page {i + 1}: text differs")
    for e in glob.glob(f"{ROOT}/expected/{job}/*.png"):
        a, b = Image.open(e).convert("RGB"), Image.open(os.path.join(work, os.path.basename(e))).convert("RGB")
        if a.size != b.size or ImageChops.difference(a, b).getbbox():
            fails.append(f"{os.path.basename(e)}: image differs")
    return s, fails, work


if __name__ == "__main__":
    jobs = sys.argv[1:] or list(EXP)
    bad = 0
    for j in jobs:
        s, fails, work = check(j)
        print(f"{'PASS' if not fails else 'FAIL'}  {j}: sheets {s['sheets_to_send']}, tops {s['tops']}, uprights {s['uprights_to_send']}, "
              f"weights {s['weights_to_send']}" + (f", quote ${s['quote_ex_gst']:,.2f} ex GST" if 'quote_ex_gst' in s else "") + f"   ({work})")
        for f in fails: print("      " + f)
        bad += bool(fails)
    sys.exit(1 if bad else 0)
