"""v1.1 rule 1 (Gus, 2026-11-01): uprights = joints (both run ends included) + 10% spare, rounded up.
External jobs: round the 40% up first, then add the 10% spare on that total, rounded up (DJ Lift 24 -> 34 -> 38).
Fire-door jobs: only the joints where an upright actually stands (Medibank 7, plus spares)."""
import json, os

import pytest

import baseline, layout_gen, titan


def job(name):
    return json.load(open(os.path.join(baseline.ROOT, "hoarding", name, "job.json")))


@pytest.mark.parametrize("joints, spare", [(10, 1), (14, 2), (18, 2), (22, 3), (7, 1)])
def test_spare_is_10_percent_of_the_joints_rounded_up(joints, spare):
    up, wind, sp, per, w = titan.for_job({"height": 4.5}, joints)
    assert (up, wind, sp) == (joints + spare, 0, spare)


@pytest.mark.parametrize("joints", [10, 20, 30, 70, 140])
def test_whole_10_percent_is_not_rounded_up_again(joints):
    # an exact 10% (10 -> 1, 70 -> 7, ...) stays exact
    assert titan.for_job({"height": 4.5}, joints)[:3] == (joints + joints // 10, 0, joints // 10)


def test_external_rounds_the_40_percent_first_then_the_spare():
    # DJ Lift, confirmed by Gus: 24 joints -> 24 + 10 = 34 -> 34 + 4 = 38 (one rounding at the end would give 37)
    up, wind, spare, per, w = titan.for_job({"height": 2.4, "external": True}, 24)
    assert (up, wind, spare, per) == (38, 10, 4, 8)


def test_both_run_ends_are_joints():
    j = job("Bikini")
    c = layout_gen.compute(j)
    assert c["uprights"][0] == 0 and c["uprights"][-1] == c["L"]


def test_fire_door_counts_only_joints_with_an_upright():
    j = job("Medibank")
    joints = titan.joins(j, layout_gen.compute(j))
    assert joints == 7
    assert titan.for_job(j, joints)[:3] == (8, 0, 1)


def test_weights_not_changed_by_rule_1():
    # Rule 2 moves the weights onto all uprights; until then they are worked out as in v1, before the spare.
    assert titan.for_job({"height": 4.5}, 10)[4] == 77
    assert titan.for_job({"height": 2.4, "external": True}, 24)[4] == 300
