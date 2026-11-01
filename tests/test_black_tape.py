"""Black skirting tape (Gus, 2026-11-02, provisional): a skirt along the full lineal metres of the job (the whole run,
returns and entry included) x 2 (100% spare, like the white tape) / 25 m rolls, rounded up. v1 sent 1 roll per job."""
import json, os

import pytest
from openpyxl import load_workbook

import baseline, layout_gen, tape

ROLLS = {"Bikini": 1, "FRED_v2": 2, "DavidJones": 2, "DavidJones1": 2, "Shrungaar": 2, "Medibank": 1, "DavidJonesLift": 2}


def job(name):
    return json.load(open(os.path.join(baseline.ROOT, "hoarding", name, "job.json")))


def test_rule_values():
    b = tape.RULES["black_tape"]
    assert (b["roll_length"], b["spare"]) == (25, 1.0)


@pytest.mark.parametrize("run_mm, rolls", [
    (10400, 1),    # 20.8 m
    (12500, 1),    # exactly 25.0 m: 1 roll, not 2
    (12501, 2),
    (24600, 2),    # DJ Lift 49.2 m
    (25000, 2),    # exactly 50.0 m
])
def test_rounding_in_whole_mm(run_mm, rolls):
    assert tape.black_rolls_mm(run_mm) == rolls


@pytest.mark.parametrize("name", baseline.JOBS)
def test_form_and_summary(name, reference_run):
    summary, work = reference_run(name)
    j = job(name)
    assert tape.black_tape(j, layout_gen.compute(j)) == ROLLS[name]
    ws = load_workbook(os.path.join(work, f"{j['prefix']}_materials.xlsx")).active
    row = next(r for r in ws.iter_rows(min_col=2, max_col=4, values_only=True) if r[0] == "Black Skirting Tape 100mm")
    assert row[1] == summary["black_tape_rolls"] == ROLLS[name]
    assert row[2] == "25m Rolls"
