"""hoarding/jobs.py: normalize(inputs) -> job.json and warnings(job, summary) (PLAN-app.md §6, step 2).

normalize turns the new-job form's inputs (as Gus gives them: entry from either end, defaults left out) into job.json.
It is checked by rebuilding every reference job.json from those inputs. warnings lists what the reviewer must know,
each with the rule it comes from; it never changes a number."""
import copy, json, os
from pathlib import Path

import pytest

import baseline, jobs
from rules import RULES


def ref(name):
    j = json.loads(Path(os.path.join(baseline.ROOT, "hoarding", name, "job.json")).read_text(encoding="utf-8"))
    j.pop("dir")
    return j


def summary(name):
    return json.loads(Path(os.path.join(baseline.ROOT, "expected", name, "run_summary.json")).read_text(encoding="utf-8"))


def without(d, *keys):
    return {k: v for k, v in d.items() if k not in keys}


# Inputs the way Gus gives them (entries from the end he measured from, as the entry notes say)
INPUTS = {
    "Bikini": {**without(ref("Bikini"), "front", "door_offset", "return", "door_width", "door_height"),
               "kind": "standard", "front": 8.0, "return": 1.2, "entry_from": "left", "entry_offset": 1.2},
    "FRED_v2": {**without(ref("FRED_v2"), "door_offset", "return", "door_width", "door_height"),
                "kind": "standard", "entry_from": "left", "entry_offset": 4.8},
    "DavidJones": {**without(ref("DavidJones"), "door_offset"), "kind": "standard", "entry_from": "right", "entry_offset": 6.0},
    "Shrungaar": {**without(ref("Shrungaar"), "front", "return", "door_offset", "corner", "faces"), "kind": "corner",
                  "faces": [{"name": "angled return", "len": 1.2, "cut": "right"}, {"name": "side", "len": 8.5, "cut": "right"},
                            {"name": "front", "len": 8.6, "entry_from": "right", "entry_offset": 4.8},
                            {"name": "right return", "len": 1.2, "cut": "left"}]},
    "Medibank": {**without(ref("Medibank"), "front", "return", "right_return", "door_offset", "faces"), "kind": "fire door",
                 "faces": [{"name": "left return", "len": 3.0, "cut": "right"},
                           {"name": "front", "len": 7.5, "entry_from": "right", "entry_offset": 1.2},
                           {"name": "right return", "len": 1.6, "cut": "left"}]},
    "DavidJonesLift": {**without(ref("DavidJonesLift"), "front", "return", "door_offset", "faces", "shape"), "kind": "U",
                       "faces": [{"name": "left return", "len": 1.6, "cut": "right"}, {"name": "left side", "len": 5.6, "cut": "right"},
                                 {"name": "front", "len": 10.2, "cut": "right"},
                                 {"name": "right side", "len": 5.6, "entry_from": "left", "entry_offset": 2.8},
                                 {"name": "right return", "len": 1.6, "cut": "left"}]},
}


@pytest.mark.parametrize("name", INPUTS)
def test_normalize_rebuilds_the_reference_job(name):
    assert jobs.normalize(INPUTS[name]) == ref(name)


def test_entry_from_the_right_end_in_whole_mm():
    # 20.0 - 6.0 - 1.6 = 12.399999999999999 in floating point; job.json must say 12.4
    j = jobs.normalize(INPUTS["DavidJones"])
    assert j["door_offset"] == 12.4


def test_defaults_come_from_rules_json():
    j = jobs.normalize(INPUTS["Bikini"])
    d = RULES["defaults"]
    assert (j["door_width"], j["door_height"]) == (d["door_width"], d["door_height"])
    j = jobs.normalize(without(INPUTS["Bikini"], "return"))
    assert j["return"] == d["return"]


def test_name_defaults_to_the_title():
    j = jobs.normalize(without(INPUTS["FRED_v2"], "name"))
    assert j["name"] == "FRED"


def test_dir_from_the_jobs_folder():
    j = jobs.normalize(INPUTS["FRED_v2"], jobs_dir=os.path.join("data", "jobs"))
    assert j["dir"] == os.path.join("data", "jobs", "FRED_v2")


def test_extra_weight_is_never_filled_in():
    i = without(INPUTS["DavidJonesLift"], "extra_weight_pct")
    assert "extra_weight_pct" not in jobs.normalize(i)


def test_inputs_are_not_changed():
    i = copy.deepcopy(INPUTS["Medibank"])
    jobs.normalize(i)
    assert i == INPUTS["Medibank"]


@pytest.mark.parametrize("change", [{"kind": "round"}, {"entry_from": "middle"}, {"colour": "red"}])
def test_bad_inputs_are_refused(change):
    with pytest.raises(ValueError):
        jobs.normalize({**INPUTS["Bikini"], **change})


def test_faces_need_one_entry_face():
    i = copy.deepcopy(INPUTS["Shrungaar"])
    del i["faces"][2]["entry_from"], i["faces"][2]["entry_offset"]
    with pytest.raises(ValueError, match="entry"):
        jobs.normalize(i)


def test_suggest_prefix():
    assert jobs.suggest_prefix("David Jones - Lift Area") == "DavidJonesLiftArea"
    assert jobs.suggest_prefix("Bikini on the Beach!") == "BikiniOnTheBeach"
    assert jobs.suggest_prefix("FRED") == "FRED"


# --- warnings -------------------------------------------------------------------------------------------------------

def rules_of(ws):
    return {w.rule for w in ws}


def leaf(path):
    d = json.loads(Path(os.path.join(baseline.ROOT, "hoarding", "rules.json")).read_text(encoding="utf-8"))
    for k in path.split("."):
        d = d[k]
    return d


@pytest.mark.parametrize("name", baseline.JOBS)
def test_every_warning_names_its_rule(name):
    ws = jobs.warnings(ref(name), summary(name))
    assert ws
    for w in ws:
        assert w.rule.startswith("CLAUDE.md §") or leaf(w.rule)["provisional"] is True, w
        assert w.message


def test_provisional_rules_every_job_uses():
    r = rules_of(jobs.warnings(ref("Bikini"), summary("Bikini")))
    assert {"materials.studs", "door_set.studs_short_length", "tape.spare", "black_tape.spare"} <= r
    assert not {"external.extra_uprights", "rate_card.bands", "CLAUDE.md §10"} & r


def test_external_job():
    r = rules_of(jobs.warnings(ref("DavidJonesLift"), summary("DavidJonesLift")))
    assert {"external.extra_uprights", "external.weights_per_upright", "rate_card.bands"} <= r


def test_pacific_fair_quote_and_poa_lines():
    ws = jobs.warnings(ref("DavidJonesLift"), summary("DavidJonesLift"))
    poa = [w for w in ws if "POA" in w.message]
    assert poa and poa[0].rule == "CLAUDE.md §12"


def test_corner_fire_door_and_tops():
    assert "CLAUDE.md §8" in rules_of(jobs.warnings(ref("Shrungaar"), summary("Shrungaar")))
    ws = jobs.warnings(ref("Medibank"), summary("Medibank"))
    assert any(w.rule == "CLAUDE.md §10" and "suggestion only" in w.message for w in ws)
    assert any(w.rule == "CLAUDE.md §3" and "offcuts" in w.message for w in ws)
    assert not any("offcuts" in w.message for w in jobs.warnings(ref("DavidJonesLift"), summary("DavidJonesLift")))


def test_entry_moved_and_estimates():
    ws = jobs.warnings(ref("Bikini"), summary("Bikini"))
    assert any(w.rule == "CLAUDE.md §1" and "entry" in w.message for w in ws)
    j = {**ref("Bikini"), "estimated": ["front", "height"]}
    est = [w for w in jobs.warnings(j, summary("Bikini")) if "estimate" in w.message]
    assert est and est[0].rule == "CLAUDE.md §1" and "front" in est[0].message


def test_hand_set_uprights():
    j = {**ref("Bikini"), "uprights": 9}
    assert any(w.rule == "CLAUDE.md §5" for w in jobs.warnings(j, summary("Bikini")))


def test_tape_switch_on_v1(monkeypatch):
    monkeypatch.setitem(jobs.RULES["tape"], "tape_rule", "v1")
    r = rules_of(jobs.warnings(ref("Bikini"), summary("Bikini")))
    assert "materials.white_tape" in r and "tape.spare" not in r


def test_warnings_do_not_change_the_job_or_summary():
    j, s = ref("Medibank"), summary("Medibank")
    j0, s0 = copy.deepcopy(j), copy.deepcopy(s)
    jobs.warnings(j, s)
    assert (j, s) == (j0, s0)
