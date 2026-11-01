"""v1.1 rule 4 (Gus, 2026-11-01): white tape rolls = total joint length / 25 m per roll, + 20% spare, rounded up.
Every joint counts: vertical joints between sheets, corners and both run ends at full hoarding height; the joint
between sheets and tops; the door: both sides (2 x door height) plus the top (door width). Replaces v1's 8 per 8.8 m."""
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
    assert t["rolls"] == 3   # 61.8 x 1.2 = 74.16 m / 25 = 2.97 -> 3


@pytest.mark.parametrize("total_mm, rolls", [
    (62500, 3),    # 62.5 x 1.2 = 75.0 m = exactly 3 rolls (floating point gives 3.0000000000000004 -> 4)
    (62501, 4),
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


@pytest.mark.parametrize("name", baseline.JOBS)
def test_form_and_summary_show_the_rolls(name, reference_run):
    summary, work = reference_run(name)
    ws = load_workbook(os.path.join(work, f"{job(name)['prefix']}_materials.xlsx")).active
    row = next(r for r in ws.iter_rows(min_col=2, max_col=4, values_only=True) if r[0] == "White Tape 50mm")
    assert row[1] == summary["white_tape_rolls"]
