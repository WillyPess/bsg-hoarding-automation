"""The engenai UI (Gus's design): sign in, sidebar, Jobs (with the Examples), New job with its bar, the job page,
Fix job, Dashboard, Activity, and the deploy settings for Render.

Every number on a screen comes from a run_summary.json (here the fake engine's, with numbers no rule would give,
so a number worked out by the app would show) or from job.json; the bar's from the engine (engine.estimate)."""
import io, json, re, sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app_helpers as H
from app import engine, settings as S, storage
from app.main import create_app
import test_app_runs as R


@pytest.fixture
def app_s(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "run_job", R.fake_engine())
    return H.make_app(tmp_path / "data")


@pytest.fixture
def gus(app_s):
    return H.logged_in(app_s[0], "gus")


def photo():
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), (200, 30, 60)).save(buf, "JPEG")
    return buf.getvalue()


FORM = {"title": "Bikini on the Beach", "site": "Pacific Fair", "client": "GPT - Pacific Fair", "drawings_sent_by": "Centre management",
        "front": "8.0", "height": "4.5", "return": "1.2", "entry_offset": "1.2", "entry_from": "left", "door_width": "", "door_height": "",
        "extra_doors": "1", "passage_sets": "0", "photo_note": "Camera for centre management", "date": "06/11/2026"}


def post(client, url, fields, files=None):
    page = client.get(url if url != "/jobs/estimate" else "/jobs/new")
    return client.post(url, data={**fields, "csrf_token": H.csrf_from(page.text)}, files=files, follow_redirects=False)


def audit(s, action):
    with closing(sqlite3.connect(s.data_dir / "bsg.sqlite")) as c:
        return c.execute("SELECT u.name, a.job, a.run, a.detail FROM audit a LEFT JOIN users u ON u.id = a.user_id WHERE a.action = ? ORDER BY a.id",
                         (action,)).fetchall()


def new_job(gus, **extra):
    r = post(gus, "/jobs/new", {**FORM, **extra}, files={"photo": ("p.jpg", photo(), "image/jpeg")})
    assert r.status_code == 303, r.text
    return R.finished(gus, r.headers["location"])


# --- sign in, sidebar -------------------------------------------------------------------------------------------------

def test_sign_in_page(app_s):
    html = TestClient(app_s[0]).get("/login").text
    for words in ("Sign in", "Hoarding jobs for shopfronts", "Username", "Password", "Every sign-in is recorded"):
        assert words in html
    assert "<aside" not in html                                         # no sidebar before signing in


def test_every_sign_in_is_recorded(app_s, gus):
    assert [(who, job) for who, job, _, _ in audit(app_s[1], "login")] == [("gus", None)]
    assert "Signed in" in gus.get("/activity").text


def test_sidebar(gus):
    html = gus.get("/dashboard").text
    side = re.search(r'<aside class="side">(.*?)</aside>', html, re.S).group(1)
    assert "LOGO" in side and ">Gus<" in side and "Sign out" in side
    assert re.findall(r'<a href="([^"]+)"', side) == ["/jobs", "/jobs/new", "/dashboard", "/activity"]
    assert re.search(r'<a href="/dashboard" class="on">', side)


# --- jobs -------------------------------------------------------------------------------------------------------------

def test_jobs_list_has_the_examples_and_the_columns(app_s, gus):
    new_job(gus)
    html = gus.get("/jobs").text
    for col in ("Job", "Site", "Height · Run", "Quote ex GST", "Created by", "Sent by", "Status"):
        assert f">{col}</th>" in html
    row = re.search(r'<tr data-job="BikiniOnTheBeach">(.*?)</tr>', html, re.S).group(1)
    assert "Bikini on the Beach" in row and "Pacific Fair" in row and "4.5 m · 9981.5 lm" in row and "$9,973.25" in row
    assert "Gus" in row and "Centre management" in row and "PDFs ready" in row
    assert re.search(r'<tr data-example="DavidJones">.*?· example</span>.*?No PDFs yet', html, re.S)


def test_jobs_filters(app_s, gus):
    new_job(gus)
    jobs = lambda **q: set(re.findall(r'data-(?:job|example)="([^"]+)"', gus.get("/jobs", params=q).text))
    assert jobs(q="centre management") == {"BikiniOnTheBeach"}            # job, client or person
    assert jobs(q="gus") == {"BikiniOnTheBeach"}
    assert "Medibank" in jobs(site="Pacific Fair") and "Bikini" not in jobs(site="Pacific Fair")
    assert jobs(who="gus") == {"BikiniOnTheBeach"}
    html = gus.get("/jobs").text
    assert '<option value="">All sites</option>' in html and '<option value="">Anyone</option>' in html


# --- new job ----------------------------------------------------------------------------------------------------------

def test_new_job_form(gus):
    html = gus.get("/jobs/new").text
    assert "Standard shopfront: return | front with entry | return" in html and "Tap to add the photo" in html
    for label in ("Job title", "Site", "Client", "Drawings sent by", "Front width", "Height", "Returns (each side)", "Entry position",
                  "Measured from", "Entry width", "Entry height", "Extra door sets", "Passage sets", "Notes for the job sheet",
                  "Dust suppression", "Ladder", "Run incl. returns", "Entry from left", "Weights / upright", "Quote ex GST (est.)"):
        assert label in html, label
    assert 'name="client" value="GPT - Pacific Fair"' in html
    assert 'value="1.6"' not in html or 'placeholder="1.6"' in html     # defaults come from rules.json as hints
    assert re.search(r'<button type="submit">Generate PDFs</button>', html)
    assert '<script src="/static/form.js"></script>' in html


def test_generate_pdfs_saves_the_job_and_runs_it(app_s, gus):
    s = app_s[1]
    page = new_job(gus, dust_suppression="on", ladder="on")
    assert 'data-status="done"' in page.text
    j = json.loads((s.data_dir / "jobs" / "BikiniOnTheBeach" / "job.json").read_text(encoding="utf-8"))
    assert (j["client"], j["drawings_sent_by"], j["dust_suppression"], j["ladder"]) == ("GPT - Pacific Fair", "Centre management", True, True)
    assert (j["extra_doors"], j["photo_note"]) == (1, "Camera for centre management") and "passage_sets" not in j
    assert (s.data_dir / "jobs" / "BikiniOnTheBeach" / "runs" / "0001" / "BikiniOnTheBeach_hoarding_markup.jpg").exists()


def test_without_a_photo_the_job_is_saved_but_not_run(app_s, gus):
    r = post(gus, "/jobs/new", FORM)
    assert r.status_code == 303 and r.headers["location"] == "/jobs/BikiniOnTheBeach"
    assert R.run_rows(app_s[1]) == []
    assert "Upload the marked-up photo to run" in gus.get("/jobs/BikiniOnTheBeach").text


def test_a_bad_photo_saves_nothing(app_s, gus):
    r = post(gus, "/jobs/new", FORM, files={"photo": ("p.jpg", b"not a photo", "image/jpeg")})
    assert r.status_code == 422 and "JPG or PNG" in r.text
    assert not (app_s[1].data_dir / "jobs" / "BikiniOnTheBeach").exists()


def test_the_bar_comes_from_the_engine(app_s, gus):
    r = post(gus, "/jobs/estimate", {**FORM, "ladder": "on"})
    assert r.status_code == 200
    _, job, _ = __import__("app.jobform", fromlist=["x"]).process({**FORM, "ladder": "on"}, storage_user(app_s[1]))
    e = engine.estimate(job, app_s[1].data_dir / "jobs" / job["prefix"])          # the engine's own numbers
    assert r.json() == {"run": f"{e['run_m']:g} lm", "entry": "1.20 m", "ladder": "Yes", "weights": str(e["weights_per_upright"]),
                        "quote": f"${e['quote_ex_gst']:,.0f}" if e["quote_ex_gst"] == int(e["quote_ex_gst"]) else f"${e['quote_ex_gst']:,.2f}"}
    assert r.json()["run"] == "10.4 lm" and r.json()["weights"] == "7"          # 8 + 2 x 1.2; 4.5 m: 7 per upright (matrix)


def storage_user(s):
    from app.users import User
    return User(storage.user_id(s, "gus"), "gus", "estimator")


def test_the_bar_before_the_form_is_complete(gus):
    r = post(gus, "/jobs/estimate", {"front": "8", "height": "4.5", "entry_offset": "1.2", "entry_from": "left"})
    assert r.json()["run"] == "11.2 lm" and r.json()["quote"] == "—"            # default returns 1.6; no site yet: no quote
    r = post(gus, "/jobs/estimate", {"front": "abc"})
    assert r.json() == {"ladder": "No"}


def test_the_bar_needs_a_login_and_the_form_token(app_s, gus):
    assert TestClient(app_s[0]).post("/jobs/estimate", data=FORM, follow_redirects=False).status_code == 303
    assert gus.post("/jobs/estimate", data=FORM).status_code == 403


# --- the job page -----------------------------------------------------------------------------------------------------

def test_job_page(app_s, gus):
    new_job(gus, dust_suppression="on")
    html = gus.get("/jobs/BikiniOnTheBeach").text
    assert "<h1>Bikini on the Beach</h1>" in html and "Pacific Fair · GPT - Pacific Fair · version 1" in html
    assert '<span class="chip done">PDFs ready</span>' in html and 'href="/jobs/BikiniOnTheBeach/edit">Fix job</a>' in html
    for words in ("Created by <b>Gus</b>", "Drawings sent by <b>Centre management</b>", "Front <span class=\"mono\">8 m</span>",
                  "Height <span class=\"mono\">4.5 m</span>", "Returns <span class=\"mono\">1.2 m</span>",
                  "Entry <span class=\"mono\">1.2 m</span> from the left end", "<b>Dust suppression</b>"):
        assert words in html, words
    stat = lambda k: re.search(rf'data-stat="{k}"><div class="v">(.*?)</div><div class="k">(.*?)</div>', html).groups()
    assert stat("run_m") == ("9981.5", "Run (lm)") and stat("sheets") == ("9983 + 8", "Sheets")      # 9991 to send
    assert stat("tops") == ("9985", "Tops") and stat("uprights") == ("9992", "Uprights") and stat("weights") == ("9997", "Weights")
    assert "+10%" not in html
    for tab in ("Hoarding limit", "Plan and elevation", "Melamine layout", "Materials"):
        assert f">{tab}</label>" in html
    downloads = re.findall(r'<a href="(/jobs/BikiniOnTheBeach/runs/1/files/[^"]+)"[^>]*>([^<]+)</a>', html)
    assert [label for _, label in downloads] == ["Hoarding Package PDF", "Quotation · $9,973.25", "Materials form (PDF)", "Materials form (Excel)"]
    assert "Email the package to the boss yourself. Downloads are recorded." in html
    assert "Job created" in html and 'href="/jobs/BikiniOnTheBeach/runs/1">PDFs generated (v1)</a>' in html


def test_downloads_are_recorded(app_s, gus):
    new_job(gus)
    gus.get("/jobs/BikiniOnTheBeach/runs/1/files/BikiniOnTheBeach_Hoarding_Package.pdf")
    gus.get("/jobs/BikiniOnTheBeach/runs/1/files/BikiniOnTheBeach_hoarding_sheet.png")            # shown on the page: not a download
    assert [(who, job, run, json.loads(d)["file"]) for who, job, run, d in audit(app_s[1], "file.downloaded")] == \
        [("gus", "BikiniOnTheBeach", 1, "BikiniOnTheBeach_Hoarding_Package.pdf")]
    assert "Downloaded BikiniOnTheBeach_Hoarding_Package.pdf" in gus.get("/activity").text


def test_no_quote_off_pacific_fair(gus):
    new_job(gus, site="Hyperdome")
    html = gus.get("/jobs/BikiniOnTheBeach").text
    assert "Quotation" not in html


# --- Fix job ----------------------------------------------------------------------------------------------------------

def test_fix_job_needs_a_note_and_makes_version_2(app_s, gus):
    s = app_s[1]
    new_job(gus)
    html = gus.get("/jobs/BikiniOnTheBeach/edit").text
    assert "Fix job: Bikini on the Beach" in html and "What was wrong" in html and 'value="8"' in html
    assert "Saved in the job's history with your name. The old version is kept." in html and ">Fix and regenerate</button>" in html
    r = post(gus, "/jobs/BikiniOnTheBeach/edit", {**FORM, "entry_from": "right"})
    assert r.status_code == 422 and "what was wrong" in r.text.lower()
    r = post(gus, "/jobs/BikiniOnTheBeach/edit", {**FORM, "entry_from": "right", "note": "Entry was measured from the wrong end"})
    assert r.status_code == 303 and r.headers["location"] == "/jobs/BikiniOnTheBeach"
    page = R.finished(gus, "/jobs/BikiniOnTheBeach")
    assert "version 2" in page.text
    [(who, job, _, d)] = audit(s, "job.corrected")
    assert (who, job, json.loads(d)["note"]) == ("gus", "BikiniOnTheBeach", "Entry was measured from the wrong end")
    assert "door_offset" in json.loads(d)["changed"]
    assert (s.data_dir / "jobs" / "BikiniOnTheBeach" / "runs" / "0001" / "job.json").exists()                # the old version is kept
    job = gus.get("/jobs/BikiniOnTheBeach").text
    assert "Job fixed" in job and "Entry was measured from the wrong end" in job and "version 2" in job


# --- dashboard, activity ----------------------------------------------------------------------------------------------

def test_dashboard_adds_up_the_run_summaries(app_s, gus, monkeypatch):
    new_job(gus)
    monkeypatch.setattr(engine, "run_job", R.fake_engine({**R.SUMMARY, "run_m": 10.4, "tops": 7}))
    new_job(gus, title="FRED", site="Hyperdome", prefix="FRED")
    post(gus, "/jobs/FRED/edit", {**FORM, "title": "FRED", "site": "Hyperdome", "note": "Height was wrong"})
    R.finished(gus, "/jobs/FRED")
    html = gus.get("/dashboard").text
    tile = lambda k: re.search(rf'data-tile="{k}"><div class="k">[^<]*</div><div class="v">(.*?)</div>', html).group(1)
    assert tile("jobs") == "2" and tile("lm") == "9991.9" and tile("quoted") == "$9,973.25" and tile("corrections") == "1"
    mat = lambda k: re.search(rf'data-mat="{k}"><div class="k">[^<]*</div><div class="v">(.*?)</div>', html).group(1)
    assert (mat("sheets"), mat("tops"), mat("uprights"), mat("weights")) == ("19982", "9992", "19984", "19994")
    assert "Lineal metres per month, by site" in html and "Pacific Fair" in html and "Hyperdome" in html
    assert re.search(r'<span>Gus</span><span class="barl"[^>]*></span><span class="mono">2</span>', html)
    assert "Height was wrong" in html


def test_activity_latest_first(app_s, gus):
    new_job(gus)
    html = gus.get("/activity").text
    for col in ("When", "Who", "What", "Job", "Note"):
        assert f">{col}</th>" in html
    whats = re.findall(r"<td>Gus</td><td>([^<]+)</td>", html)
    assert whats[0] == "PDFs generated (v1)" and whats[-1] == "Signed in" and "Job created" in whats
    assert 'href="/jobs/BikiniOnTheBeach">Bikini on the Beach</a>' in html


# --- deploy (Render) --------------------------------------------------------------------------------------------------

def test_this_pc_only_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("BSG_DEPLOY", raising=False)
    monkeypatch.setenv("PORT", "10000")
    s = S.load(tmp_path)
    assert (s.host, s.port, s.deploy) == ("127.0.0.1", 8000, False)
    (tmp_path / "config.toml").write_text('[server]\nhost = "0.0.0.0"\n', encoding="utf-8")
    with pytest.raises(S.ConfigError, match="deploy"):
        S.load(tmp_path)


@pytest.mark.parametrize("how", ["env", "config"])
def test_deploy_listens_on_all_addresses_with_render_port(tmp_path, monkeypatch, how):
    monkeypatch.setenv("PORT", "10000")
    if how == "env":
        monkeypatch.setenv("BSG_DEPLOY", "1")
    else:
        monkeypatch.delenv("BSG_DEPLOY", raising=False)
        S.load(tmp_path)
        p = tmp_path / "config.toml"
        p.write_text(p.read_text(encoding="utf-8").replace("deploy = false", "deploy = true"), encoding="utf-8")
    s = S.load(tmp_path)
    assert (s.host, s.port, s.deploy) == ("0.0.0.0", 10000, True)


def test_deploy_cookies_are_secure_and_the_address_comes_from_the_proxy(tmp_path, monkeypatch):
    monkeypatch.setenv("BSG_DEPLOY", "1")
    app, s = H.make_app(tmp_path / "data")
    c = TestClient(app, base_url="https://testserver")
    page = c.get("/login")
    assert "secure" in page.headers["set-cookie"].lower()
    assert page.headers["strict-transport-security"] == "max-age=31536000"
    r = c.post("/login", data={"name": "gus", "password": H.PASSWORD, "csrf_token": H.csrf_from(page.text)},
               headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}, follow_redirects=False)
    assert r.status_code == 303 and "secure" in r.headers["set-cookie"].lower()
    with closing(sqlite3.connect(s.data_dir / "bsg.sqlite")) as db:
        assert db.execute("SELECT ip FROM login_attempts").fetchall() == [("203.0.113.7",)]


def test_off_deploy_the_header_is_ignored(app_s):
    c = TestClient(app_s[0])
    H.login(c)
    c2 = TestClient(app_s[0])
    page = c2.get("/login")
    c2.post("/login", data={"name": "gus", "password": "wrong", "csrf_token": H.csrf_from(page.text)}, headers={"X-Forwarded-For": "203.0.113.7"})
    with closing(sqlite3.connect(app_s[1].data_dir / "bsg.sqlite")) as db:
        assert {ip for (ip,) in db.execute("SELECT ip FROM login_attempts")} == {"testclient"}
    assert "secure" not in c2.get("/login").headers["set-cookie"].lower()


def test_healthz_is_public_and_says_nothing_else(app_s):
    r = TestClient(app_s[0]).get("/healthz", follow_redirects=False)
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert TestClient(app_s[0]).get("/health.json", follow_redirects=False).status_code == 303    # the details need a login
