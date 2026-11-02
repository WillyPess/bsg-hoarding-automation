"""v1.1 rule 4 (Gus, 2026-11-01): white tape rolls = total joint length / 25 m per roll, + spare, rounded up.
Gus 2026-11-02: rolls are 25 m, the spare is 100% (they always send almost double: changes on site mean removing tape
and applying new), and the joint calculation is switched on (tape.tape_rule = "joints").
Every joint counts: vertical joints between sheets, corners and both run ends at full hoarding height; the joint
between sheets and tops; the door: both sides (2 x door height) plus the top (door width).

Readings A and B (Gus 2026-11-02): the door sides and the door top count as written, also on a full-height door.
The switch stays: tape.tape_rule = "joints" (now) or "v1" (8 rolls per 8.8 m). The joints numbers are always in the summary."""
import json, os

import pytest
from openpyxl import load_workbook

import baseline, layout_gen, tape


def job(name):
    return json.load(open(os.path.join(baseline.ROOT, "hoarding", name, "job.json")))


def test_bikini_by_hand():
    # 10 vertical joints x 4.5 = 45.0, sheets/tops joint along the 10.4 run, door 2 x 2.4 + 1.6 = 6.4
    j = job("Bikini")
    t = tape.white_tape(j, layout_gen.compute(j))
    assert t["vertical_joints"] == 10
    assert (t["vertical_mm"], t["tops_mm"], t["door_mm"], t["total_mm"]) == (45000, 10400, 6400, 61800)
    assert t["rolls"] == 5   # 61.8 x 2 = 123.6 m / 25 = 4.94 -> 5


@pytest.mark.parametrize("total_mm, rolls", [
    (62500, 5),    # 62.5 x 2 = 125.0 m = exactly 5 rolls
    (62501, 6),
    (1, 1),
    (0, 0),
])
def test_rolls_round_up_in_integer_maths(total_mm, rolls):
    assert tape.rolls(total_mm) == rolls


def test_no_tops_no_tops_joint():
    # DJ Lift: 2.4 m on 2400 sheets, no tops
    j = job("DavidJonesLift")
    assert tape.white_tape(j, layout_gen.compute(j))["tops_mm"] == 0


def test_fire_door_tapes_every_joint_not_only_the_uprights():
    # Medibank: uprights stand at 7 joints only, but every sheet joint, both corners and both run ends get tape
    j = job("Medibank")
    c = layout_gen.compute(j)
    xs = tape.vertical_joints(j, c)
    assert set(round(u * 1000) for u in c["uprights"]) <= set(xs)
    assert {0, 3000, 10500, 12100} <= set(xs)
    assert len(xs) > len(c["uprights"])


@pytest.mark.parametrize("name", ["Bikini", "FRED_v2", "DavidJones", "Shrungaar", "DavidJonesLift"])
def test_vertical_joints_are_the_upright_joints_on_normal_jobs(name):
    j = job(name)
    c = layout_gen.compute(j)
    assert tape.vertical_joints(j, c) == sorted(round(u * 1000) for u in c["uprights"])


V1 = {"Bikini": 10, "FRED_v2": 13, "DavidJones": 22, "DavidJones1": 22, "Shrungaar": 18, "Medibank": 11, "DavidJonesLift": 23, "Bikini_3000": 10, "Bikini_2400": 10, "Kiosk_PF": 9}
JOINTS = {"Bikini": 5, "FRED_v2": 7, "DavidJones": 11, "DavidJones1": 11, "Shrungaar": 8, "Medibank": 6, "DavidJonesLift": 6,
          "Bikini_3000": 3, "Bikini_2400": 3, "Kiosk_PF": 1}   # rule 6 test jobs: no tops joint below 3.6 m


def test_switch_is_on_with_a_100_percent_spare():
    assert (tape.RULES["tape"]["tape_rule"], tape.RULES["tape"]["spare"], tape.RULES["tape"]["roll_length"]) == ("joints", 1.0, 25)


@pytest.mark.parametrize("name", baseline.JOBS)
def test_both_rules(name):
    j = job(name)
    c = layout_gen.compute(j)
    assert tape.rolls_for_job(j, c, "v1") == V1[name]
    assert tape.rolls_for_job(j, c, "joints") == JOINTS[name]


def test_the_switch_picks_the_rule(monkeypatch):
    j = job("Bikini")
    c = layout_gen.compute(j)
    monkeypatch.setitem(tape.RULES["tape"], "tape_rule", "joints")
    assert tape.rolls_for_job(j, c) == 5
    monkeypatch.setitem(tape.RULES["tape"], "tape_rule", "v1")
    assert tape.rolls_for_job(j, c) == 10
    monkeypatch.setitem(tape.RULES["tape"], "tape_rule", "metres")
    with pytest.raises(ValueError, match="tape_rule"):
        tape.rolls_for_job(j, c)


@pytest.mark.parametrize("name", baseline.JOBS)
def test_form_and_summary_show_the_rolls(name, reference_run):
    summary, work = reference_run(name)
    ws = load_workbook(os.path.join(work, f"{job(name)['prefix']}_materials.xlsx")).active
    row = next(r for r in ws.iter_rows(min_col=2, max_col=4, values_only=True) if r[0] == "White Tape 50mm")
    assert row[1] == summary["white_tape_rolls"] == summary["white_tape_joints_rolls"] == JOINTS[name]
    assert summary["white_tape_rule"] == "joints"
