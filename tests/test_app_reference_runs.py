"""Demo PR A (PLAN-app.md, Demo scope): each of the 10 reference jobs, run through the app with the real engine, matches
expected/: the same checks as tests/test_reference_jobs.py, on the run folder the Run button produced. Also checks the
results page shows the engine's numbers and offers the files, and that hoarding/ is left as it was."""
import json, re
from pathlib import Path

import pytest

import app_helpers as H
import baseline
import test_reference_jobs as R
from test_app_runs import count, finished, press_run, tree

HOARDING = Path(H.ROOT) / "hoarding"


@pytest.fixture(scope="module")
def app_run(tmp_path_factory):
    """run(job) -> (client, results page, summary, run folder). Each reference job runs once in this module."""
    app, s = H.make_app(tmp_path_factory.mktemp("app_runs") / "data")
    client = H.logged_in(app)
    done = {}

    def run(job):
        if job not in done:
            before = tree(HOARDING / job)
            r = press_run(client, f"/examples/{job}")
            assert r.status_code == 303, r.text
            page = finished(client, r.headers["location"], seconds=300)
            assert page.status_code == 200 and 'data-status="done"' in page.text, page.text
            assert tree(HOARDING / job) == before, f"hoarding/{job} changed"
            folder = s.data_dir / "jobs" / f"example-{job}" / "runs" / "0001"
            done[job] = (client, page.text, json.loads((folder / "run_summary.json").read_text(encoding="utf-8")), str(folder))
        return done[job]
    return run


@pytest.mark.parametrize("job", baseline.JOBS)
def test_counts(job, app_run):
    _, _, summary, _ = app_run(job)
    R.check_counts(job, summary)


@pytest.mark.parametrize("job", baseline.JOBS)
def test_materials_form(job, app_run):
    _, _, _, work = app_run(job)
    R.check_materials_form(job, work)


@pytest.mark.parametrize("job", baseline.JOBS)
def test_drawings_are_the_same_as_a_run_by_hand(job, app_run, reference_run):
    """PLAN-app.md §1, same engine, same outputs: pixel for pixel, on any machine. (test_drawings_match_baseline
    compares with the stored PNGs for this OS; a failed one leaves _DIFF.png files behind, hence the filter.)"""
    _, _, _, work = app_run(job)
    _, by_hand = reference_run(job)
    drawings = lambda folder: {n: h for n, h in baseline.snapshot(folder)["png"].items() if not n.endswith("_DIFF.png")}
    assert drawings(work) == drawings(by_hand)


@pytest.mark.parametrize("job", baseline.JOBS)
def test_drawings_match_baseline(job, app_run):
    _, _, _, work = app_run(job)
    R.check_drawings(job, work)


@pytest.mark.parametrize("job", baseline.JOBS)
def test_documents_match_baseline(job, app_run):
    _, _, _, work = app_run(job)
    R.check_documents(job, work)


@pytest.mark.parametrize("job", baseline.JOBS)
def test_results_page(job, app_run):
    client, html, summary, work = app_run(job)
    want = {k: v for k, v in R.EXPECTED[job].items() if not k.endswith("_note")}
    for key in ("sheets_to_send", "tops", "uprights_to_send", "anti_tampers_to_send", "total_weights_to_send", "white_tape_rolls", "black_tape_rolls"):
        assert count(html, key) == str(want[key]), key
    P = R.prefix(job)
    base = f"/examples/{job}/runs/1/files/"
    for name in (f"{P}_hoarding_sheet.png", f"{P}_melamine_layout.png"):
        assert f'<img class="drawing" src="{base}{name}"' in html
    links = [u[len(base):] for u in re.findall(rf'<a class="button" href="({re.escape(base)}[^"]+)"', html)]
    quote = [n for n in baseline.load(job)["pdf"] if "Quotation" in n]    # the approved documents say which jobs have a quote
    assert links == [f"{P}_Hoarding_Package.pdf", f"{P}_materials.pdf", f"{P}_materials.xlsx"] + quote
    for name in links:
        r = client.get(base + name)
        assert r.status_code == 200 and r.content == (Path(work) / name).read_bytes() and "attachment" in r.headers["content-disposition"]
        assert r.content[:4] == (b"PK\x03\x04" if name.endswith(".xlsx") else b"%PDF")


def test_david_jones_ground_on_its_job_page(app_run):
    """engenai UI: the job page of the David Jones Ground example shows the engine's numbers, with the real engine:
    21 sheets (19 + 2), 20 tops, 25 uprights, 175 weights and a $7,656 quote (CLAUDE.md, reference results)."""
    client, _, summary, _ = app_run("DavidJones")
    html = client.get("/examples/DavidJones").text
    stat = lambda k: re.search(rf'data-stat="{k}"><div class="v">(.*?)</div>', html).group(1)
    assert (summary["layout_sheets"], summary["sheets_to_send"]) == (19, 21)
    assert (stat("run_m"), stat("sheets"), stat("tops"), stat("uprights"), stat("weights")) == ("23.2", "19 + 2", "20", "25", "175")
    assert "Quotation · $7,656</a>" in html
    row = re.search(r'<tr data-example="DavidJones">(.*?)</tr>', client.get("/jobs").text, re.S).group(1)
    assert "4.5 m · 23.2 lm" in row and "$7,656" in row and "PDFs ready" in row
