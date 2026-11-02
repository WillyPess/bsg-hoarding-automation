"""v1.1 rule 8 (Gus, 2026-11-01): external jobs ask "This job is external. Add extra weight? If yes, how many percent?"
The answer is job.json extra_weight_pct (0 = none). It is applied last, on the total weights (all uprights x 8),
rounded up, and shown as a separate line. It is never picked automatically: run_job stops and asks when it is missing."""
import json, os, shutil
from pathlib import Path

import pytest
from openpyxl import load_workbook

import baseline, run_job, titan

EXT = {"height": 2.4, "external": True}


@pytest.mark.parametrize("weights, pct, extra", [
    (304, 0, 0),
    (304, 10, 31),     # 30.4 -> 31
    (304, 12.5, 38),   # exactly 38
    (50, 10, 5),       # 50 x 1.1 = 55.000000000000007 in floating point: must stay 5 extra, not 6
    (30, 10, 3),       # 30 x 0.1 = 3.0000000000000004
    (1, 1, 1),
])
def test_extra_is_a_percentage_of_the_total_rounded_up(weights, pct, extra):
    assert titan.extra_weights({**EXT, "extra_weight_pct": pct}, weights) == extra


def test_missing_answer_asks_the_question():
    with pytest.raises(titan.ExtraWeightMissing, match="This job is external. Add extra weight"):
        titan.extra_weights(EXT, 304)


def test_internal_jobs_have_no_extra_weight():
    assert titan.extra_weights({"height": 4.5}, 77) == 0
    with pytest.raises(ValueError):
        titan.extra_weights({"height": 4.5, "extra_weight_pct": 10}, 77)
    with pytest.raises(ValueError):
        titan.extra_weights({**EXT, "extra_weight_pct": -5}, 304)


def copy_dj_lift(tmp_path, **change):
    work = str(tmp_path / "DavidJonesLift")
    shutil.copytree(os.path.join(baseline.ROOT, "hoarding", "DavidJonesLift"), work)
    p = os.path.join(work, "job.json")
    j = json.loads(Path(p).read_text(encoding="utf-8"))
    for k, v in change.items():
        if v is None:
            j.pop(k, None)
        else:
            j[k] = v
    with open(p, "w", encoding="utf-8") as f:
        json.dump(j, f)
    return work


def test_run_job_stops_and_asks_without_filling_it_in(tmp_path):
    work = copy_dj_lift(tmp_path, extra_weight_pct=None)
    before = sorted(os.listdir(work))
    with pytest.raises(SystemExit, match="This job is external. Add extra weight"):
        run_job.run(work)
    assert sorted(os.listdir(work)) == before                              # no outputs written
    assert "extra_weight_pct" not in json.loads(Path(os.path.join(work, "job.json")).read_text(encoding="utf-8"))   # never filled in


def titan_rows(xlsx):
    ws = load_workbook(xlsx).active
    return {r[0]: (r[1], r[2]) for r in ws.iter_rows(min_col=2, max_col=4, values_only=True) if r[0]}


def test_dj_lift_answer_is_0(reference_run):
    summary, work = reference_run("DavidJonesLift")
    assert (summary["extra_weight_pct"], summary["extra_weights"], summary["weights_to_send"], summary["total_weights_to_send"]) == (0, 0, 304, 304)
    assert titan_rows(os.path.join(work, "DavidJonesLift_materials.xlsx"))["Extra Counterweights"][0] == 0


def test_extra_weight_is_a_separate_line(tmp_path):
    work = copy_dj_lift(tmp_path, extra_weight_pct=10)
    s = run_job.run(work)
    assert (s["weights_to_send"], s["extra_weights"], s["total_weights_to_send"]) == (304, 31, 335)
    rows = titan_rows(os.path.join(work, "DavidJonesLift_materials.xlsx"))
    assert rows["Counterweights"][0] == 304
    assert rows["Extra Counterweights"] == (31, "10% extra weight on 304 (asked for this external job)")


def test_internal_form_has_no_extra_line(reference_run):
    _, work = reference_run("Bikini")
    assert "Extra Counterweights" not in titan_rows(os.path.join(work, "Bikini_materials.xlsx"))
