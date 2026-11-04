"""hoarding/validate.py: check(job) -> list of problems (field + message). Empty list = the job can run.
Only checks inputs against the rules already in CLAUDE.md / rules.json; it never computes a quantity."""
import copy, json, os, shutil
from pathlib import Path

import pytest

import baseline, run_job, titan, validate


def job(name):
    return json.loads(Path(os.path.join(baseline.ROOT, "hoarding", name, "job.json")).read_text(encoding="utf-8"))


def fields(problems):
    return [p.field for p in problems]


@pytest.mark.parametrize("name", baseline.JOBS)
def test_reference_jobs_are_valid(name):
    assert validate.check(job(name)) == []


def test_problem_reads_as_text():
    p = validate.Problem("height", "must be more than 0")
    assert str(p) == "height: must be more than 0"


@pytest.mark.parametrize("key", ["name", "prefix", "title", "site", "date", "front", "return", "height", "door_offset", "door_width"])
def test_required_fields(key):
    j = job("Bikini"); del j[key]
    assert key in fields(validate.check(j))


@pytest.mark.parametrize("key", ["title", "site", "prefix"])
def test_blank_text_is_missing(key):
    j = job("Bikini"); j[key] = "  "
    assert key in fields(validate.check(j))


@pytest.mark.parametrize("prefix", ["FRED v2", "a/b", "..", "x:y", "é"])
def test_prefix_must_be_safe_for_file_names(prefix):
    j = job("Bikini"); j["prefix"] = prefix
    assert "prefix" in fields(validate.check(j))


@pytest.mark.parametrize("key, value", [("front", 0), ("height", -1), ("door_width", 0), ("return", -0.1), ("height", "4.5"), ("front", True)])
def test_lengths_are_positive_numbers(key, value):
    j = job("Bikini"); j[key] = value
    assert key in fields(validate.check(j))


def test_height_above_the_weight_matrix_asks_gus():
    j = job("Bikini"); j["height"] = 7.5
    [p] = [p for p in validate.check(j) if p.field == "height"]
    assert "7.2" in p.message and "Gus" in p.message
    j["height"] = 7.2
    assert validate.check(j) == []


def test_entry_inside_the_front():
    j = job("Bikini"); j["door_offset"] = j["front"] - j["door_width"] + 0.1
    assert "door_offset" in fields(validate.check(j))
    j["door_offset"] = -0.1
    assert "door_offset" in fields(validate.check(j))
    j["door_offset"] = j["front"] - j["door_width"]   # entry ends exactly at the corner: fine
    assert validate.check(j) == []


def test_door_not_taller_than_the_hoarding():
    j = job("Bikini"); j["door_height"] = 4.6
    assert "door_height" in fields(validate.check(j))


def test_external_jobs_are_2_4_m():
    j = job("DavidJonesLift"); j["height"] = 3.0
    assert "height" in fields(validate.check(j))


def test_external_without_extra_weight_asks_the_question():
    j = job("DavidJonesLift"); del j["extra_weight_pct"]
    [p] = validate.check(j)
    assert p.field == "extra_weight_pct" and titan.QUESTION in p.message


@pytest.mark.parametrize("pct", [-5, "10", None])
def test_extra_weight_must_be_a_number_0_or_more(pct):
    j = job("DavidJonesLift"); j["extra_weight_pct"] = pct
    assert "extra_weight_pct" in fields(validate.check(j))


def test_extra_weight_only_on_external_jobs():
    j = job("Bikini"); j["extra_weight_pct"] = 10
    assert "extra_weight_pct" in fields(validate.check(j))


@pytest.mark.parametrize("value", [0, -2, 3.5, "12"])
def test_hand_set_uprights(value):
    j = job("Bikini"); j["uprights"] = value
    assert "uprights" in fields(validate.check(j))


def test_faces_need_exactly_one_entry():
    j = job("Shrungaar")
    del j["faces"][2]["door_offset"]
    assert "faces" in fields(validate.check(j))
    j = job("Shrungaar"); j["faces"][1]["door_offset"] = 1.0
    assert "faces" in fields(validate.check(j))


def test_entry_inside_its_face():
    j = job("DavidJonesLift"); j["faces"][3]["door_offset"] = 4.1   # 4.1 + 1.6 > 5.6
    assert "faces[3].door_offset" in fields(validate.check(j))


def test_face_lengths():
    j = job("Shrungaar"); j["faces"][0]["len"] = 0
    assert "faces[0].len" in fields(validate.check(j))
    j = job("Shrungaar"); j["faces"][0]["cut"] = "middle"
    assert "faces[0].cut" in fields(validate.check(j))


def test_u_jobs_have_5_faces():
    j = job("DavidJonesLift"); j["faces"].pop()
    assert "faces" in fields(validate.check(j))


def test_fire_door_track():
    j = job("Medibank"); j["track"]["face"] = "back wall"
    assert "track.face" in fields(validate.check(j))
    j = job("Medibank"); j["track"]["len"] = 3.5   # longer than the 3.0 left return
    assert "track.len" in fields(validate.check(j))
    j = job("Medibank"); j["track"]["studs"] = 0
    assert "track.studs" in fields(validate.check(j))
    j = job("Medibank"); del j["shopfront"]
    assert "shopfront" in fields(validate.check(j))


def test_several_problems_at_once():
    j = job("Bikini"); j["title"] = ""; j["height"] = 0; j["prefix"] = "a b"
    assert {"title", "height", "prefix"} <= set(fields(validate.check(j)))


def test_check_does_not_change_the_job():
    j = job("Medibank"); before = copy.deepcopy(j)
    validate.check(j)
    assert j == before


def test_run_job_refuses_an_invalid_job_before_writing(tmp_path):
    work = str(tmp_path / "Bikini")
    shutil.copytree(os.path.join(baseline.ROOT, "hoarding", "Bikini"), work)
    p = os.path.join(work, "job.json"); j = json.loads(Path(p).read_text(encoding="utf-8")); j["height"] = 0; j["title"] = ""
    with open(p, "w", encoding="utf-8") as f:
        json.dump(j, f)
    before = sorted(os.listdir(work))
    with pytest.raises(SystemExit) as e:
        run_job.run(work)
    assert "height" in str(e.value) and "title" in str(e.value)
    assert sorted(os.listdir(work)) == before
