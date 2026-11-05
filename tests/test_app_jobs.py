"""Step 4 of PLAN-app.md §11: the job list, the Examples tab and the new/edit job form (standard jobs + kiosk).

The form only collects inputs: jobs.normalize turns them into job.json (defaults from rules.json, the entry from
either end) and validate.check decides what's wrong. Nothing is written while there are problems, and every create
or edit is in the audit with who and when."""
import json, re, sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import app_helpers as H
from app import storage
from app.main import create_app

H.sys.path.insert(0, str(Path(H.ROOT) / "hoarding"))
import jobs as engine_jobs   # noqa: E402  the engine's normalize / warnings / suggest_prefix
from rules import RULES      # noqa: E402

GOOD = {"title": "Bikini on the Beach", "site": "Hyperdome", "site_other": "", "date": "20/10/2026", "prefix": "Bikini",
        "front": "8.0", "return": "1.2", "height": "4.5", "door_width": "1.6", "door_height": "2.4",
        "entry_from": "left", "entry_offset": "1.2", "entry_note": ", in front of the shop entry"}


@pytest.fixture
def app_s(tmp_path):
    return H.make_app(tmp_path / "data")


@pytest.fixture
def gus(app_s):
    return H.logged_in(app_s[0], "gus")


def post_form(client, url, fields):
    page = client.get(url)
    return client.post(url, data={**fields, "csrf_token": H.csrf_from(page.text)}, follow_redirects=False)


def job_json(s, folder):
    return json.loads((s.data_dir / "jobs" / folder / "job.json").read_text(encoding="utf-8"))


def audit_rows(s):
    with closing(sqlite3.connect(s.data_dir / "bsg.sqlite")) as c:
        return c.execute("SELECT a.action, a.job, u.name, a.at, a.detail FROM audit a LEFT JOIN users u ON u.id = a.user_id ORDER BY a.id").fetchall()


def field_error(html, field):
    m = re.search(rf'<p class="field-error" id="err-{re.escape(field)}">(.*?)</p>', html, re.S)
    return m.group(1).strip() if m else None


# --- the job list -----------------------------------------------------------------------------------------------------

def test_home_is_the_job_list(gus):
    r = gus.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/jobs"


def test_empty_job_list(gus):
    r = gus.get("/jobs")
    assert r.status_code == 200 and "No jobs yet" in r.text and 'href="/jobs/new"' in r.text


def make(s, prefix, **kw):
    j = engine_jobs.normalize({"kind": "standard", "title": kw.pop("title", prefix), "site": kw.pop("site", "Hyperdome"),
                               "date": "01/11/2026", "prefix": prefix, "front": 8.0, "height": 4.5,
                               "entry_from": "left", "entry_offset": 1.2, **kw})
    storage.create_job(s, j, storage.user_id(s, "gus"))
    return j


def test_job_list_columns(app_s, gus):
    s = app_s[1]
    j = make(s, "FRED_v2", title="FRED", site="Pacific Fair")
    html = gus.get("/jobs").text
    row = re.search(r'<tr data-job="FRED_v2">(.*?)</tr>', html, re.S).group(1)
    assert "FRED" in row and "Pacific Fair" in row and "standard" in row and "draft" in row
    assert "—" in row                                                  # no run yet
    n = len(engine_jobs.warnings(j, {}))                               # the engine counts the warnings, not the app
    assert f'<td class="warnings">{n}</td>' in row


def test_job_list_search_by_title_or_site(app_s, gus):
    s = app_s[1]
    make(s, "Bikini", title="Bikini on the Beach", site="Hyperdome")
    make(s, "FRED_v2", title="FRED", site="Pacific Fair")
    make(s, "Medibank", title="Medibank", site="Pacific Fair")
    found = lambda q: set(re.findall(r'data-job="([^"]+)"', gus.get("/jobs", params={"q": q}).text))
    assert found("bikini") == {"Bikini"}
    assert found("pacific") == {"FRED_v2", "Medibank"}
    assert found("MEDI") == {"Medibank"}
    assert found("nothing like this") == set()
    assert found("") == {"Bikini", "FRED_v2", "Medibank"}


def test_both_users_see_every_job(app_s, gus):
    make(app_s[1], "Bikini")
    boss = H.logged_in(app_s[0], "boss")
    assert 'data-job="Bikini"' in boss.get("/jobs").text


# --- Examples ---------------------------------------------------------------------------------------------------------

def test_examples_list_the_reference_jobs(gus):
    html = gus.get("/examples").text
    names = set(re.findall(r'data-example="([^"]+)"', html))
    assert {"Bikini", "FRED_v2", "DavidJones", "Shrungaar", "Medibank", "DavidJonesLift", "Kiosk_PF"} <= names
    assert "FRED" not in names                                         # the legacy FRED job (old scripts) is not an example


def test_an_example_is_read_only(gus):
    r = gus.get("/examples/Medibank")
    assert r.status_code == 200 and "Medibank" in r.text and "read-only" in r.text.lower()
    posts = re.findall(r'<form method="post" action="([^"]*)"', r.text)
    assert posts == ["/logout", "/examples/Medibank/run"]              # no form on the page but logout and Run (on a copy)
    assert gus.post("/examples/Medibank", data={}).status_code in (403, 405)
    for path in ("/jobs/Medibank", "/jobs/Medibank/edit"):              # not a job of the app: can't be edited or approved
        assert gus.get(path).status_code == 404


def test_examples_are_not_jobs(gus):
    assert 'data-job=' not in gus.get("/jobs").text


@pytest.mark.parametrize("name", ["../app", "FRED", "nope", "CON"])
def test_unknown_example(gus, name):
    assert gus.get(f"/examples/{name}").status_code == 404


# --- the new-job form -------------------------------------------------------------------------------------------------

def test_form_fields(gus):
    html = gus.get("/jobs/new").text
    assert 'name="csrf_token"' in html
    site = re.search(r'<select name="site".*?</select>', html, re.S).group(0)
    assert "selected" not in site and "Pacific Fair" in site and "Hyperdome" in site   # site always asked: nothing pre-selected
    assert re.search(r'<input type="radio" name="entry_from" value="left"(?![^>]*checked)', html)
    assert re.search(r'<input type="radio" name="entry_from" value="right"(?![^>]*checked)', html)
    assert 'name="kiosk"' in html
    for f in ("front", "return", "height", "door_width", "door_height", "entry_offset"):
        assert f'name="estimate_{f}"' in html, f
    assert "gus" in html and 'name="by"' not in html                 # prepared by = the logged-in user, not a field
    assert "Corner, U-shaped, fire-door and external jobs" in html    # said plainly, not hidden


def test_form_shows_the_rules_defaults_as_hints(gus):
    html = gus.get("/jobs/new").text
    d = RULES["defaults"]
    assert f'placeholder="{d["return"]:g}"' in html and f'placeholder="{d["door_width"]:g}"' in html


def test_create_a_standard_job(app_s, gus):
    s = app_s[1]
    r = post_form(gus, "/jobs/new", GOOD)
    assert r.status_code == 303 and r.headers["location"] == "/jobs/Bikini"
    expected = engine_jobs.normalize({"kind": "standard", "title": GOOD["title"], "site": "Hyperdome", "date": "20/10/2026",
                                      "prefix": "Bikini", "front": 8.0, "return": 1.2, "height": 4.5, "door_width": 1.6,
                                      "door_height": 2.4, "entry_from": "left", "entry_offset": 1.2,
                                      "entry_note": ", in front of the shop entry", "by": "gus"})
    assert job_json(s, "Bikini") == expected
    actions = [(a, j, u) for a, j, u, *_ in audit_rows(s)]
    assert ("job.created", "Bikini", "gus") in actions
    assert "Bikini on the Beach" in gus.get("/jobs/Bikini").text


def test_prefix_suggested_from_the_title(app_s, gus):
    r = post_form(gus, "/jobs/new", {**GOOD, "prefix": "", "title": "David Jones - Lift Area"})
    assert r.headers["location"] == "/jobs/" + engine_jobs.suggest_prefix("David Jones - Lift Area")


def test_entry_from_the_right_end(app_s, gus):
    post_form(gus, "/jobs/new", {**GOOD, "entry_from": "right", "entry_offset": "5.2"})   # 8.0 - 5.2 - 1.6 = 1.2 from the left
    assert job_json(app_s[1], "Bikini")["door_offset"] == 1.2


def test_defaults_come_from_rules_json_through_normalize(app_s, gus):
    post_form(gus, "/jobs/new", {**GOOD, "return": "", "door_width": "", "door_height": ""})
    j, d = job_json(app_s[1], "Bikini"), RULES["defaults"]
    assert (j["return"], j["door_width"], j["door_height"]) == (d["return"], d["door_width"], d["door_height"])


def test_kiosk(app_s, gus):
    r = post_form(gus, "/jobs/new", {**GOOD, "kiosk": "on", "height": "1.2", "door_height": "", "front": "6.0", "entry_offset": "2.4"})
    assert r.status_code == 303, r.text
    j = job_json(app_s[1], "Bikini")
    assert j["kiosk"] is True and j["door_height"] == RULES["kiosk_door"]["leaf_height"]


def test_estimate_ticks(app_s, gus):
    post_form(gus, "/jobs/new", {**GOOD, "estimate_front": "on", "estimate_entry_offset": "on"})
    assert job_json(app_s[1], "Bikini")["estimated"] == ["front", "door_offset"]


def test_other_site(app_s, gus):
    post_form(gus, "/jobs/new", {**GOOD, "site": "other", "site_other": "Robina Town Centre"})
    assert job_json(app_s[1], "Bikini")["site"] == "Robina Town Centre"


def test_fields_not_on_the_form_are_ignored(app_s, gus):
    # external, faces, extra weight etc. can't come in through this form (not built yet)
    post_form(gus, "/jobs/new", {**GOOD, "external": "on", "extra_weight_pct": "10", "faces": "x", "by": "someone else"})
    j = job_json(app_s[1], "Bikini")
    assert "external" not in j and "extra_weight_pct" not in j and "faces" not in j and j["by"] == "gus"


# --- problems: shown next to their fields, nothing written ------------------------------------------------------------

def nothing_written(s):
    assert not (s.data_dir / "jobs").exists() or not any((s.data_dir / "jobs").iterdir())
    assert not [r for r in audit_rows(s) if r[0].startswith("job.")]


@pytest.mark.parametrize("change, field, words", [
    ({"height": "7.5"}, "height", "7.2"),                                # validate: above the weight matrix
    ({"front": "abc"}, "front", "number"),                               # not a number
    ({"front": ""}, "front", "required"),
    ({"site": ""}, "site", "choose"),                                    # site always asked
    ({"site": "other", "site_other": ""}, "site", "choose"),
    ({"entry_from": ""}, "entry_from", "left or the right"),
    ({"entry_offset": "7.0"}, "entry_offset", "past the end"),          # validate's door_offset, shown on the entry field
    ({"door_height": "5"}, "door_height", "taller"),
    ({"prefix": "CON"}, "prefix", "reserved"),
    ({"prefix": "a b"}, "prefix", "letters"),
    ({"title": ""}, "title", "required"),
    ({"kiosk": "on", "height": "2.4"}, "height", "1.2"),                 # a kiosk is 1.2 m: ask Gus
])
def test_problem_next_to_its_field(app_s, gus, change, field, words):
    r = post_form(gus, "/jobs/new", {**GOOD, **change})
    assert r.status_code == 422
    msg = field_error(r.text, field)
    assert msg and words.lower() in msg.lower(), (field, msg)
    nothing_written(app_s[1])


def test_all_problems_at_once_and_the_values_are_kept(app_s, gus):
    r = post_form(gus, "/jobs/new", {**GOOD, "height": "7.5", "front": "abc", "site": ""})
    assert r.status_code == 422
    assert field_error(r.text, "height") and field_error(r.text, "front") and field_error(r.text, "site")
    assert 'value="abc"' in r.text and 'value="7.5"' in r.text          # what was typed stays in the form
    nothing_written(app_s[1])


def test_duplicate_prefix(app_s, gus):
    post_form(gus, "/jobs/new", GOOD)
    r = post_form(gus, "/jobs/new", {**GOOD, "prefix": "bikini", "title": "Another"})
    assert r.status_code == 422 and "already" in field_error(r.text, "prefix")


def test_a_1_2_m_job_without_kiosk_is_saved_with_the_engine_warning(app_s, gus):
    r = post_form(gus, "/jobs/new", {**GOOD, "height": "1.2", "door_height": "1.2"})
    assert r.status_code == 303
    assert "is it a kiosk" in gus.get("/jobs/Bikini").text.lower()


# --- editing ----------------------------------------------------------------------------------------------------------

def test_edit_form_is_prefilled(app_s, gus):
    post_form(gus, "/jobs/new", {**GOOD, "estimate_height": "on"})
    html = gus.get("/jobs/Bikini/edit").text
    assert 'value="Bikini on the Beach"' in html and 'value="4.5"' in html
    assert re.search(r'name="estimate_height"[^>]*checked', html)
    assert re.search(r'<option value="Hyperdome" selected', html)


def test_edit_a_job(app_s, gus):
    s = app_s[1]
    post_form(gus, "/jobs/new", GOOD)
    boss = H.logged_in(app_s[0], "boss")
    r = post_form(boss, "/jobs/Bikini/edit", {**GOOD, "height": "4.2"})
    assert r.status_code == 303 and r.headers["location"] == "/jobs/Bikini"
    assert job_json(s, "Bikini")["height"] == 4.2
    [(action, job, who, at, detail)] = [r for r in audit_rows(s) if r[0] == "job.edited"]
    assert (job, who) == ("Bikini", "boss") and at > 0 and "height" in json.loads(detail)["changed"]


def test_edit_keeps_the_prefix_and_the_keys_the_form_doesnt_show(app_s, gus):
    s = app_s[1]
    post_form(gus, "/jobs/new", GOOD)
    p = s.data_dir / "jobs" / "Bikini" / "job.json"
    p.write_text(json.dumps({**job_json(s, "Bikini"), "photo_h": 88, "quote_date": "01/11/2026"}), encoding="utf-8")
    post_form(gus, "/jobs/Bikini/edit", {**GOOD, "prefix": "Other", "height": "4.2"})
    j = job_json(s, "Bikini")
    assert (j["prefix"], j["photo_h"], j["quote_date"], j["height"]) == ("Bikini", 88, "01/11/2026", 4.2)
    assert not (s.data_dir / "jobs" / "Other").exists()


def test_a_bad_edit_changes_nothing(app_s, gus):
    s = app_s[1]
    post_form(gus, "/jobs/new", GOOD)
    before = job_json(s, "Bikini")
    r = post_form(gus, "/jobs/Bikini/edit", {**GOOD, "height": "9"})
    assert r.status_code == 422 and field_error(r.text, "height")
    assert job_json(s, "Bikini") == before
    assert not [x for x in audit_rows(s) if x[0] == "job.edited"]


def test_no_edit_form_for_job_types_not_built_yet(app_s, gus):
    s = app_s[1]
    j = json.loads((Path(H.ROOT) / "hoarding" / "Shrungaar" / "job.json").read_text(encoding="utf-8")); j.pop("dir")
    storage.create_job(s, j, storage.user_id(s, "gus"))               # a corner job, e.g. copied in by hand
    html = gus.get("/jobs/Shrungaar/edit").text
    assert "corner" in html.lower() and "can't be edited here yet" in html and 'name="front"' not in html
    assert post_form(gus, "/jobs/Shrungaar/edit", GOOD).status_code == 409


def test_unknown_job(gus):
    for path in ("/jobs/Nope", "/jobs/Nope/edit", "/jobs/..%2Fapp"):
        assert gus.get(path).status_code == 404


def test_no_message_from_stand_in_values(app_s, gus):
    # when the front can't be read, the entry can't be checked against it: say nothing about the entry rather than
    # something wrong (the stand-ins used to check the other fields must never show up in a message)
    r = post_form(gus, "/jobs/new", {**GOOD, "front": "7,5x"})
    assert field_error(r.text, "front") and field_error(r.text, "entry_offset") is None
    r = post_form(gus, "/jobs/new", {**GOOD, "entry_from": ""})
    assert field_error(r.text, "entry_from") and field_error(r.text, "entry_offset") is None


def test_kiosk_shows_as_kiosk_in_the_list(app_s, gus):
    post_form(gus, "/jobs/new", {**GOOD, "kiosk": "on", "height": "1.2", "door_height": "", "front": "6.0", "entry_offset": "2.4"})
    row = re.search(r'<tr data-job="Bikini">(.*?)</tr>', gus.get("/jobs").text, re.S).group(1)
    assert "<td>kiosk</td>" in row
