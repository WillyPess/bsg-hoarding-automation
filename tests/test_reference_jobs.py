"""The 7 reference jobs (expected/), run through the full pipeline: counts, materials form, drawings and documents.

Counts and the materials form are the approved v1 numbers. Drawings (PNG) and documents (PDF text) are compared
with expected/<Job>/baseline.json; if a change is intended, check the new outputs and run tests/update_baseline.py.
"""
import json, os
from pathlib import Path

import pytest

import baseline
from check_fixtures import cells

ROOT = baseline.ROOT
EXPECTED = json.loads(Path(os.path.join(ROOT, "expected", "expected_counts.json")).read_text(encoding="utf-8"))["jobs"]
UPDATE = "If the change is intended, check the new files in {work} and run: python tests/update_baseline.py {job}"


def prefix(job):
    return json.loads(Path(os.path.join(ROOT, "hoarding", job, "job.json")).read_text(encoding="utf-8"))["prefix"]


def check_counts(job, summary):
    want = {k: v for k, v in EXPECTED[job].items() if not k.endswith("_note")}
    got = {k: summary.get(k) for k in want}
    assert got == want


@pytest.mark.parametrize("job", baseline.JOBS)
def test_counts(job, reference_run):
    """Sheets, tops, uprights, weights and quote match the numbers approved by Gus (expected_counts.json)."""
    summary, _ = reference_run(job)
    check_counts(job, summary)


def check_materials_form(job, work):
    P = prefix(job)
    want, got = cells(os.path.join(ROOT, "expected", job, f"{P}_materials.xlsx")), cells(os.path.join(work, f"{P}_materials.xlsx"))
    diff = {k: (want.get(k), got.get(k)) for k in sorted(set(want) | set(got)) if want.get(k) != got.get(k)}
    assert not diff, f"materials cells (row, col): (expected, got) {diff}"


@pytest.mark.parametrize("job", baseline.JOBS)
def test_materials_form(job, reference_run):
    """Every cell of the materials xlsx matches the form delivered to Gus."""
    _, work = reference_run(job)
    check_materials_form(job, work)


@pytest.mark.parametrize("job", baseline.JOBS)
def test_drawings_match_baseline(job, reference_run):
    """Every PNG (grid sheet, melamine layout, check plans) matches the approved baseline.

    Compared with the images stored for this OS (expected/<Job>/png/<os>/): at most baseline.MAX_PCT % of the pixels
    may change. A job with no folder for this OS fails and says how to create it."""
    _, work = reference_run(job)
    check_drawings(job, work)


def check_drawings(job, work):
    store = baseline.png_dir(job)
    want = sorted(n for n in os.listdir(store) if n.endswith(".png")) if os.path.isdir(store) else []
    assert want, (f"No stored drawings for {job} on {baseline.OS}: {store} does not exist. "
                  f"Create it with: python tests/update_baseline.py --store-pngs {job}")
    got = baseline.snapshot(work)["png"]
    assert sorted(got) == want, f"PNG files differ: expected {want}, got {sorted(got)}"
    report, changed = [], []
    for n in want:
        mask = os.path.join(work, n[:-4] + "_DIFF.png")
        pct, raw = baseline.drawing_diff(os.path.join(store, n), os.path.join(work, n), mask)
        report.append(f"{n}: {pct:.3f} % changed ({raw:.3f} % of pixels not identical)")
        if pct > baseline.MAX_PCT:
            changed.append(n)
        else:
            os.remove(mask)
    print("\n".join(report))
    assert not changed, (f"drawings changed by more than {baseline.MAX_PCT} % of the pixels:\n" + "\n".join(report)
                         + f"\nChanged pixels are magenta in {work}/*_DIFF.png. " + UPDATE.format(work=work, job=job))


def first_difference(a, b):
    i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return f"...{a[max(0, i - 60):i + 60]}...\n   got: ...{b[max(0, i - 60):i + 60]}..."


@pytest.mark.parametrize("job", baseline.JOBS)
def test_documents_match_baseline(job, reference_run):
    """Every PDF (package, materials, quotation) has the same pages and text as the approved baseline."""
    _, work = reference_run(job)
    check_documents(job, work)


def check_documents(job, work):
    want, got = baseline.load(job)["pdf"], baseline.snapshot(work)["pdf"]
    assert sorted(got) == sorted(want), f"PDF files differ: expected {sorted(want)}, got {sorted(got)}"
    problems = []
    for name, pages in want.items():
        if len(got[name]) != len(pages):
            problems.append(f"{name}: {len(pages)} pages expected, got {len(got[name])}")
        for i, (a, b) in enumerate(zip(pages, got[name])):
            if a != b:
                problems.append(f"{name} page {i + 1}:\nexpected: {first_difference(a, b)}")
    assert not problems, "\n".join(problems) + "\n" + UPDATE.format(work=work, job=job)
