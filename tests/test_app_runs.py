"""Demo PR A (PLAN-app.md, Demo scope): the Run button, the "running..." state and the results page.

The engine is faked here, so these tests are fast and every number on the page is a marker: the page must show what
the run folder holds, nothing it worked out itself. tests/test_app_reference_runs.py runs the real engine."""
import json, re, shutil, sqlite3, threading, time
from contextlib import closing
from pathlib import Path

import pytest

import app_helpers as H
from app import engine, storage
from app.main import create_app

HOARDING = Path(H.ROOT) / "hoarding"
SUMMARY = {"run_m": 9981.5, "height_m": 9982.5, "layout_sheets": 9983, "sheets_to_send": 9991, "sheet_h": 9984.5,
           "tops": 9985, "tops_from_offcuts": "99 x 1200 x 900", "uprights_at_joins": 9986, "extra_uprights": 0, "spare_uprights": 9987,
           "uprights_to_send": 9992, "anti_tampers_to_send": 9993, "weights_per_upright": 9988, "weights_to_send": 9994,
           "white_tape_rolls": 9995, "black_tape_rolls": 9996, "total_weights_to_send": 9997}
QUOTE = {"quote_lm": 9971.5, "quote_rate": 9972, "quote_ex_gst": 9973.25, "quote_gst": 9974.5, "quote_total": 9975.75, "quote_poa_lines": 2}
OUTPUTS = ("_hoarding_sheet.png", "_melamine_layout.png", "_materials.xlsx", "_materials.pdf", "_Hoarding_Package.pdf")


def job(prefix="Bikini", site="Hyperdome", **kw):
    return {"name": prefix, "prefix": prefix, "date": "01/11/2026", "title": f"{prefix} title", "site": site, "by": "gus", "front": 8.0,
            "return": 1.6, "height": 4.5, "door_offset": 1.2, "door_width": 1.6, "door_height": 2.4, **kw}


def fake_engine(summary=None):
    """Stands in for engine.run_job: writes the output files and the summary, like run_job.py does."""
    def run(folder, timeout=None):
        folder = Path(folder)
        j = json.loads((folder / "job.json").read_text(encoding="utf-8"))
        P = j["prefix"]
        for end in OUTPUTS:
            (folder / f"{P}{end}").write_bytes(f"{P}{end}".encode())
        s = dict(summary or SUMMARY)
        if j.get("site") == "Pacific Fair":
            (folder / j.get("quote_file", f"{P}_Quotation.pdf")).write_bytes(b"quote")
            s.update(QUOTE)
        (folder / "run_summary.json").write_text(json.dumps(s), encoding="utf-8")
        return None
    return run


@pytest.fixture
def app_s(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "run_job", fake_engine())
    return H.make_app(tmp_path / "data")


@pytest.fixture
def gus(app_s):
    return H.logged_in(app_s[0], "gus")


def make(s, prefix="Bikini", photo=True, **kw):
    """A job, with its marked-up photo (since demo PR B, Run waits for it; test_app_photo.py covers the job without)."""
    storage.create_job(s, job(prefix, **kw), storage.user_id(s, "gus"))
    if photo:
        storage.write_job_file(s, prefix, f"{prefix}_hoarding_markup.jpg", b"the photo")


def press_run(client, page_url):
    """Press the Run button on a page: the form must be there, with its CSRF token."""
    html = client.get(page_url).text
    m = re.search(r'<form method="post" action="([^"]+/run)">(.*?)</form>', html, re.S)
    assert m, f"no Run button on {page_url}"
    assert ">Run<" in m.group(2)
    return client.post(m.group(1), data={"csrf_token": H.csrf_from(m.group(2))}, follow_redirects=False)


def finished(client, url, seconds=60):
    """The run page once the run is over."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        r = client.get(url)
        if r.status_code != 200 or 'data-status="running"' not in r.text:
            return r
        time.sleep(0.02)
    raise AssertionError(f"{url} still running after {seconds} s")


def run_rows(s):
    with closing(sqlite3.connect(s.data_dir / "bsg.sqlite")) as c:
        return c.execute("SELECT job, number, status, error FROM runs ORDER BY job, number").fetchall()


def actions(s):
    with closing(sqlite3.connect(s.data_dir / "bsg.sqlite")) as c:
        return [(a, j, n) for a, j, n in c.execute("SELECT action, job, run FROM audit ORDER BY id")]


def count(html, key):
    m = re.search(rf'<tr data-key="{key}"[^>]*>.*?<td>(.*?)</td>', html, re.S)
    return m.group(1).strip() if m else None


def tree(folder):
    return {str(p.relative_to(folder)): (p.stat().st_size, p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


# --- the Run button ---------------------------------------------------------------------------------------------------

def test_run_on_a_job_goes_into_a_new_run_folder(app_s, gus):
    s = app_s[1]
    make(s)
    storage.write_job_file(s, "Bikini", "Bikini_hoarding_markup.jpg", b"the photo")
    r = press_run(gus, "/jobs/Bikini")
    assert r.status_code == 303 and r.headers["location"] == "/jobs/Bikini/runs/1"
    assert finished(gus, "/jobs/Bikini/runs/1").status_code == 200
    r2 = press_run(gus, "/jobs/Bikini")
    assert r2.headers["location"] == "/jobs/Bikini/runs/2"
    finished(gus, "/jobs/Bikini/runs/2")
    runs = s.data_dir / "jobs" / "Bikini" / "runs"
    assert (runs / "0001" / "Bikini_Hoarding_Package.pdf").exists() and (runs / "0002" / "Bikini_Hoarding_Package.pdf").exists()
    assert (runs / "0001" / "Bikini_hoarding_markup.jpg").read_bytes() == b"the photo"     # the run has its own inputs
    assert not (s.data_dir / "jobs" / "Bikini" / "Bikini_Hoarding_Package.pdf").exists()   # nothing lands next to job.json
    assert run_rows(s) == [("Bikini", 1, "done", None), ("Bikini", 2, "done", None)]
    assert ("run.started", "Bikini", 1) in actions(s) and ("run.finished", "Bikini", 1) in actions(s)


def test_the_job_page_lists_its_runs(app_s, gus):
    make(app_s[1])
    assert "/jobs/Bikini/runs/1" not in gus.get("/jobs/Bikini").text
    press_run(gus, "/jobs/Bikini")
    finished(gus, "/jobs/Bikini/runs/1")
    assert 'href="/jobs/Bikini/runs/1"' in gus.get("/jobs/Bikini").text


def test_the_job_list_shows_the_run(app_s, gus):
    make(app_s[1])
    press_run(gus, "/jobs/Bikini")
    finished(gus, "/jobs/Bikini/runs/1")
    row = re.search(r'<tr data-job="Bikini">(.*?)</tr>', gus.get("/jobs").text, re.S).group(1)
    assert '"status run"' in row


def test_every_kind_of_job_has_the_button(app_s, gus):
    s = app_s[1]
    j = json.loads((HOARDING / "Shrungaar" / "job.json").read_text(encoding="utf-8")); j.pop("dir")
    storage.create_job(s, j, storage.user_id(s, "gus"))       # a corner job: no form for it yet, but it can run
    storage.write_job_file(s, "Shrungaar", "Shrungaar_hoarding_markup.jpg", b"the photo")
    assert press_run(gus, "/jobs/Shrungaar").status_code == 303
    finished(gus, "/jobs/Shrungaar/runs/1")


def test_run_needs_login_and_a_job(app_s, gus):
    from fastapi.testclient import TestClient
    make(app_s[1])
    anon = TestClient(app_s[0])
    assert anon.post("/jobs/Bikini/run", data={}, follow_redirects=False).status_code in (303, 403)
    assert anon.get("/jobs/Bikini/runs/1", follow_redirects=False).status_code == 303
    token = H.csrf_from(gus.get("/jobs/Bikini").text)
    assert gus.post("/jobs/Nope/run", data={"csrf_token": token}).status_code == 404
    assert gus.post("/jobs/Bikini/run", data={}).status_code == 403
    assert gus.get("/jobs/Bikini/runs/1").status_code == 404
    assert run_rows(app_s[1]) == []


# --- running... -------------------------------------------------------------------------------------------------------

@pytest.fixture
def blocked(monkeypatch):
    """An engine that waits until the test lets it finish."""
    go, started = threading.Event(), threading.Event()
    real = fake_engine()

    def run(folder, timeout=None):
        started.set()
        assert go.wait(30)
        return real(folder)
    monkeypatch.setattr(engine, "run_job", run)
    yield go, started
    go.set()


def test_running_state_then_results(app_s, gus, blocked):
    go, started = blocked
    make(app_s[1])
    press_run(gus, "/jobs/Bikini")
    assert started.wait(10)
    html = gus.get("/jobs/Bikini/runs/1").text
    assert 'data-status="running"' in html and "Running" in html
    assert re.search(r'<meta http-equiv="refresh" content="\d+">', html)            # updates by itself, no JavaScript
    assert 'data-key=' not in html and "/files/" not in html
    go.set()
    html = finished(gus, "/jobs/Bikini/runs/1").text
    assert 'http-equiv="refresh"' not in html and "Running" not in html
    assert count(html, "sheets_to_send") == "9991"


def test_a_second_press_goes_to_the_run_in_progress(app_s, gus, blocked):
    go, started = blocked
    make(app_s[1])
    assert press_run(gus, "/jobs/Bikini").headers["location"] == "/jobs/Bikini/runs/1"
    assert started.wait(10)
    assert press_run(gus, "/jobs/Bikini").headers["location"] == "/jobs/Bikini/runs/1"
    go.set()
    finished(gus, "/jobs/Bikini/runs/1")
    assert [n for _, n, *_ in run_rows(app_s[1])] == [1]


def test_runs_take_turns(app_s, gus, monkeypatch):
    # LibreOffice can't convert two files at once with one profile: one engine run at a time, across all jobs
    running, most = [], []
    real = fake_engine()

    def run(folder, timeout=None):
        running.append(folder); most.append(len(running))
        time.sleep(0.05)
        real(folder)
        running.remove(folder)
    monkeypatch.setattr(engine, "run_job", run)
    make(app_s[1], "One"); make(app_s[1], "Two"); make(app_s[1], "Three")
    for name in ("One", "Two", "Three"):
        press_run(gus, f"/jobs/{name}")
    for name in ("One", "Two", "Three"):
        finished(gus, f"/jobs/{name}/runs/1")
    assert max(most) == 1


def test_a_run_cut_off_by_a_restart_is_marked_interrupted(app_s, gus):
    s = app_s[1]
    make(s)
    storage.start_run(s, "Bikini", storage.user_id(s, "gus"))            # the app stopped mid-run: no worker is left
    html = H.logged_in(create_app(s), "gus").get("/jobs/Bikini/runs/1").text
    assert 'data-status="running"' not in html and "interrupted" in html.lower() and "http-equiv" not in html
    assert run_rows(s) == [("Bikini", 1, "interrupted", None)]
    assert ("run.interrupted", "Bikini", 1) in actions(s)


# --- a failed run -----------------------------------------------------------------------------------------------------

def test_a_failed_run_shows_what_the_engine_said(app_s, gus, monkeypatch):
    monkeypatch.setattr(engine, "run_job", lambda folder, timeout=None: "Bikini: job.json can't run:\n  - height <too> high")
    make(app_s[1])
    press_run(gus, "/jobs/Bikini")
    html = finished(gus, "/jobs/Bikini/runs/1").text
    assert 'data-status="failed"' in html and "http-equiv" not in html
    assert "height &lt;too&gt; high" in html                                   # the engine's own text, escaped
    assert "/files/" not in html and 'data-key=' not in html
    assert run_rows(app_s[1]) == [("Bikini", 1, "failed", "Bikini: job.json can't run:\n  - height <too> high")]
    assert press_run(gus, "/jobs/Bikini/runs/1").status_code == 303            # run again from the failed page


def test_a_crash_in_the_bridge_still_ends_the_run(app_s, gus, monkeypatch):
    def boom(folder, timeout=None):
        raise OSError("disk full")
    monkeypatch.setattr(engine, "run_job", boom)
    make(app_s[1])
    press_run(gus, "/jobs/Bikini")
    assert "disk full" in finished(gus, "/jobs/Bikini/runs/1").text
    assert run_rows(app_s[1])[0][2] == "failed"


# --- the results page -------------------------------------------------------------------------------------------------

def results(client, s, prefix="Bikini", **kw):
    make(s, prefix, **kw)
    press_run(client, f"/jobs/{prefix}")
    return finished(client, f"/jobs/{prefix}/runs/1").text


def test_results_show_exactly_what_the_engine_wrote(app_s, gus):
    # PLAN-app.md §1: every number on the page comes from run_summary.json
    html = results(gus, app_s[1])
    for key, value in {"sheets_to_send": "9991", "tops": "9985", "uprights_to_send": "9992", "anti_tampers_to_send": "9993",
                       "weights_per_upright": "9988", "weights_to_send": "9994", "total_weights_to_send": "9997",
                       "white_tape_rolls": "9995", "black_tape_rolls": "9996", "run_m": "9981.5 m", "height_m": "9982.5 m"}.items():
        assert count(html, key) == value, key
    assert "99 x 1200 x 900" in html
    assert count(html, "extra_uprights") is None                                # 0 on an internal job: nothing to say
    assert count(html, "quote_total") is None                                   # not Pacific Fair


def test_results_show_both_drawings(app_s, gus):
    html = results(gus, app_s[1])
    for name in ("Bikini_hoarding_sheet.png", "Bikini_melamine_layout.png"):
        src = f"/jobs/Bikini/runs/1/files/{name}"
        assert f'<img class="drawing" src="{src}"' in html
        r = gus.get(src)
        assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content == name.encode()
        assert "attachment" not in r.headers.get("content-disposition", "")


def test_results_show_the_engine_warnings(app_s, gus):
    html = results(gus, app_s[1], entry_note=", set <here>", estimated=["front"])
    want = engine.warnings(job(entry_note=", set <here>", estimated=["front"]), SUMMARY)
    assert want
    for w in want:
        assert w.rule in html
    assert "99 x 1200 x 900" in re.search(r'<ul class="warnings-list">.*?</ul>', html, re.S).group(0)   # with this run's summary
    assert "set &lt;here&gt;" in html


def test_the_warnings_are_for_the_inputs_of_this_run(app_s, gus):
    s = app_s[1]
    results(gus, s)
    storage.update_job(s, "Bikini", job(estimated=["front"]), storage.user_id(s, "gus"))     # edited after the run
    assert "site measurements" not in gus.get("/jobs/Bikini/runs/1").text


def test_download_links(app_s, gus):
    html = results(gus, app_s[1])
    links = re.findall(r'<a class="button" href="(/jobs/Bikini/runs/1/files/[^"]+)"', html)
    assert links == [f"/jobs/Bikini/runs/1/files/Bikini{end}" for end in ("_Hoarding_Package.pdf", "_materials.pdf", "_materials.xlsx")]
    for url in links:
        r = gus.get(url)
        name = url.rsplit("/", 1)[1]
        assert r.status_code == 200 and r.content == name.encode()
        assert "attachment" in r.headers["content-disposition"] and name in r.headers["content-disposition"]


def test_the_quote_is_offered_on_pacific_fair(app_s, gus):
    html = results(gus, app_s[1], site="Pacific Fair")
    url = "/jobs/Bikini/runs/1/files/Bikini_Quotation.pdf"
    assert f'href="{url}"' in html
    assert gus.get(url).content == b"quote"
    for key, value in {"quote_lm": "9971.5 lm", "quote_rate": "$9,972.00", "quote_ex_gst": "$9,973.25", "quote_gst": "$9,974.50",
                       "quote_total": "$9,975.75", "quote_poa_lines": "2"}.items():
        assert count(html, key) == value, key


def test_the_quote_keeps_its_own_file_name(app_s, gus):
    html = results(gus, app_s[1], "FRED_v2", site="Pacific Fair", quote_file="FRED_Quotation.pdf")
    url = "/jobs/FRED_v2/runs/1/files/FRED_Quotation.pdf"
    assert f'href="{url}"' in html and gus.get(url).content == b"quote"


def test_results_of_an_external_job_show_the_extra_weight(app_s, gus, monkeypatch):
    monkeypatch.setattr(engine, "run_job", fake_engine({**SUMMARY, "extra_uprights": 9961, "extra_weight_pct": 9962, "extra_weights": 9963}))
    html = results(gus, app_s[1], external=True, extra_weight_pct=9962)
    assert (count(html, "extra_uprights"), count(html, "extra_weight_pct"), count(html, "extra_weights")) == ("9961", "9962%", "9963")


@pytest.mark.parametrize("name", ["job.json", "engine.json", "run_summary.json", "engine.log", "Bikini_hoarding_markup.jpg", "nope.pdf", "..%2Fjob.json", "..%5Cjob.json"])
def test_only_the_results_can_be_downloaded(app_s, gus, name):
    results(gus, app_s[1])
    assert gus.get(f"/jobs/Bikini/runs/1/files/{name}").status_code == 404


def test_a_file_needs_a_real_run(app_s, gus):
    results(gus, app_s[1])
    for url in ("/jobs/Bikini/runs/2", "/jobs/Bikini/runs/2/files/Bikini_materials.pdf", "/jobs/Nope/runs/1", "/jobs/Bikini/runs/-1", "/jobs/Bikini/runs/x"):
        assert gus.get(url).status_code in (404, 422), url


def test_results_stay_after_the_job_is_edited(app_s, gus):
    s = app_s[1]
    results(gus, s)
    storage.update_job(s, "Bikini", job(height=4.2), storage.user_id(s, "gus"))
    assert count(gus.get("/jobs/Bikini/runs/1").text, "sheets_to_send") == "9991"


# --- Examples run on a copy in the data folder, never in hoarding/ ----------------------------------------------------

def test_an_example_runs_on_a_copy_in_the_data_folder(app_s, gus, monkeypatch):
    s = app_s[1]
    seen = []
    real = fake_engine()

    def run(folder, timeout=None):
        seen.append(Path(folder).resolve())
        return real(folder)
    monkeypatch.setattr(engine, "run_job", run)
    before = tree(HOARDING / "DavidJonesLift")
    r = press_run(gus, "/examples/DavidJonesLift")
    assert r.status_code == 303 and r.headers["location"] == "/examples/DavidJonesLift/runs/1"
    html = finished(gus, "/examples/DavidJonesLift/runs/1").text
    assert seen == [(s.data_dir / "jobs" / "example-DavidJonesLift" / "runs" / "0001").resolve()]
    assert tree(HOARDING / "DavidJonesLift") == before                          # hoarding/ untouched
    for name in ("job.json", "quote_extras.json", "DavidJonesLift_hoarding_markup.jpg"):
        assert (seen[0] / name).read_bytes() == (HOARDING / "DavidJonesLift" / name).read_bytes()
    assert count(html, "sheets_to_send") == "9991"
    assert 'href="/examples/DavidJonesLift/runs/1/files/DavidJonesLift_Hoarding_Package.pdf"' in html
    assert gus.get("/examples/DavidJonesLift/runs/1/files/DavidJonesLift_Quotation.pdf").content == b"quote"
    assert 'href="/examples/DavidJonesLift/runs/1"' in gus.get("/examples/DavidJonesLift").text
    assert press_run(gus, "/examples/DavidJonesLift").headers["location"] == "/examples/DavidJonesLift/runs/2"
    finished(gus, "/examples/DavidJonesLift/runs/2")


def test_the_copy_follows_the_reference_job(app_s, gus, tmp_path, monkeypatch):
    # job.json or an input changed (or removed) in hoarding/: the next run uses what is there now
    from app import pages_jobs
    src = tmp_path / "hoarding"
    shutil.copytree(HOARDING / "DavidJonesLift", src / "DavidJonesLift")
    monkeypatch.setattr(pages_jobs, "EXAMPLES", src)
    press_run(gus, "/examples/DavidJonesLift")
    finished(gus, "/examples/DavidJonesLift/runs/1")
    (src / "DavidJonesLift" / "quote_extras.json").unlink()
    press_run(gus, "/examples/DavidJonesLift")
    finished(gus, "/examples/DavidJonesLift/runs/2")
    runs = app_s[1].data_dir / "jobs" / "example-DavidJonesLift" / "runs"
    assert (runs / "0001" / "quote_extras.json").exists() and not (runs / "0002" / "quote_extras.json").exists()


def test_generated_files_in_hoarding_are_not_copied(app_s, gus, tmp_path, monkeypatch):
    # hoarding/<job> may hold the outputs of a run by hand (git-ignored): they are not inputs
    from app import pages_jobs
    src = tmp_path / "hoarding"
    shutil.copytree(HOARDING / "Bikini", src / "Bikini")
    (src / "Bikini" / "Bikini_Hoarding_Package.pdf").write_bytes(b"old")
    (src / "Bikini" / "run_summary.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pages_jobs, "EXAMPLES", src)
    monkeypatch.setattr(engine, "run_job", lambda folder, timeout=None: "stop here")
    press_run(gus, "/examples/Bikini")
    finished(gus, "/examples/Bikini/runs/1")
    run = app_s[1].data_dir / "jobs" / "example-Bikini" / "runs" / "0001"
    assert sorted(p.name for p in run.iterdir() if p.name != "engine.json") == ["Bikini_hoarding_markup.jpg", "job.json"]


def test_an_example_copy_is_not_a_job(app_s, gus):
    s = app_s[1]
    press_run(gus, "/examples/Bikini")
    finished(gus, "/examples/Bikini/runs/1")
    assert "data-job=" not in gus.get("/jobs").text
    assert "data-job=" not in gus.get("/jobs", params={"q": "bikini"}).text
    for path in ("/jobs/example-Bikini", "/jobs/example-Bikini/edit", "/jobs/example-Bikini/runs/1", "/jobs/Bikini/runs/1",
                 "/jobs/example-Bikini/runs/1/files/Bikini_materials.pdf"):
        assert gus.get(path).status_code == 404, path
    token = H.csrf_from(gus.get("/jobs").text)
    assert gus.post("/jobs/example-Bikini/run", data={"csrf_token": token}).status_code == 404


def test_rebuild_index_keeps_the_copy_out_of_the_job_list(app_s, gus):
    s = app_s[1]
    make(s)
    press_run(gus, "/examples/Bikini")
    finished(gus, "/examples/Bikini/runs/1")
    assert storage.rebuild_index(s) == {"jobs": 2, "runs": 1}
    assert set(re.findall(r'data-job="([^"]+)"', gus.get("/jobs").text)) == {"Bikini"}
    assert count(gus.get("/examples/Bikini/runs/1").text, "sheets_to_send") == "9991"


def test_a_job_and_an_example_can_share_a_name(app_s, gus):
    s = app_s[1]
    make(s)                                                                     # the job "Bikini" and the example Bikini
    press_run(gus, "/examples/Bikini")
    finished(gus, "/examples/Bikini/runs/1")
    assert gus.get("/jobs/Bikini/runs/1").status_code == 404
    assert press_run(gus, "/jobs/Bikini").headers["location"] == "/jobs/Bikini/runs/1"
    finished(gus, "/jobs/Bikini/runs/1")


def test_the_example_prefix_is_kept(app_s, gus):
    page = gus.get("/jobs/new")
    r = gus.post("/jobs/new", data={"title": "A job", "site": "Hyperdome", "date": "01/11/2026", "prefix": "Example-Bikini", "front": "8.0", "height": "4.5",
                                    "entry_from": "left", "entry_offset": "1.2", "csrf_token": H.csrf_from(page.text)}, follow_redirects=False)
    assert r.status_code == 422 and "kept for the Examples" in r.text
    assert not (app_s[1].data_dir / "jobs" / "Example-Bikini").exists()


@pytest.mark.parametrize("name", ["FRED", "nope", "CON"])
def test_an_unknown_example_cant_run(gus, name):
    token = H.csrf_from(gus.get("/jobs").text)
    assert gus.post(f"/examples/{name}/run", data={"csrf_token": token}).status_code == 404
    assert gus.get(f"/examples/{name}/runs/1").status_code == 404


# --- the bridge to the real engine ------------------------------------------------------------------------------------

def test_run_job_says_what_is_wrong_with_the_inputs(tmp_path):
    (tmp_path / "job.json").write_text(json.dumps(job(height=7.5)), encoding="utf-8")
    error = engine.run_job(tmp_path)
    assert "can't run" in error and "7.2" in error and "Traceback" not in error
    assert (tmp_path / "engine.log").exists()


def test_run_job_without_the_photo_says_so_before_doing_anything(tmp_path):
    (tmp_path / "job.json").write_text(json.dumps(job()), encoding="utf-8")
    error = engine.run_job(tmp_path)
    assert "Bikini_hoarding_markup.jpg" in error and "Traceback" not in error
    assert sorted(p.name for p in tmp_path.iterdir()) == ["engine.log", "job.json"]


def test_run_job_that_never_ends(tmp_path):
    (tmp_path / "job.json").write_text(json.dumps(job()), encoding="utf-8")
    error = engine.run_job(tmp_path, timeout=0.001)
    assert "didn't finish" in error


def test_a_run_writes_the_run_row_with_the_user(app_s, gus):
    s = app_s[1]
    make(s)
    press_run(gus, "/jobs/Bikini")
    finished(gus, "/jobs/Bikini/runs/1")
    with closing(sqlite3.connect(s.data_dir / "bsg.sqlite")) as c:
        assert c.execute("SELECT started_by FROM runs").fetchone()[0] == storage.user_id(s, "gus")
    assert "gus" in gus.get("/jobs/Bikini/runs/1").text
    e = json.loads((s.data_dir / "jobs" / "Bikini" / "runs" / "0001" / "engine.json").read_text(encoding="utf-8"))
    assert e["ok"] is True and e["seconds"] >= 0
