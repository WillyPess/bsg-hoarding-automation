"""Rounding traps: counts that are "rounded up" must not jump by one on floating-point noise."""
import layout_gen, titan
from quotes import quote_gen


def test_weights_50_x_1_1_is_55():
    # 10 uprights x 5 weights (3.6 m row) x 1.1 = 55.00000000000001 in floating point
    assert 10 * 5 * 1.1 > 55
    assert titan.counterweights(10, 3.6) == (5, 55)
    assert titan.for_job({"height": 3.6}, 10) == (10, 0, 5, 55)


def test_sheets_21_6_over_1_2_is_18():
    # 21.6 / 1.2 = 18.000000000000004 in floating point
    assert 21.6 / 1.2 > 18
    assert layout_gen.nfull(21.6) == 18
    c = layout_gen.compute({"faces": [{"name": "front", "len": 21.6}], "door_width": 0, "height": 3.6})
    assert (c["sheets"], c["bins"]) == (18, [])


def test_weights_spare_rounds_up():
    # Medibank: 7 uprights x 6 weights x 1.1 = 46.2 -> 47
    assert titan.counterweights(7, 4.2) == (6, 47)


def test_external_extra_uprights_round_up():
    # DJ Lift: 24 x 0.4 = 9.6 -> 10 extra uprights; 34 x 8 x 1.1 = 299.2 -> 300 weights
    assert titan.for_job({"height": 2.4, "extra_uprights": 0.4, "weights_per_upright": 8}, 24) == (34, 10, 8, 300)


def quote(**job):
    return quote_gen.compute({"return": 1.6, **job})


def test_quote_height_band_at_exact_limits():
    assert quote(front=7.0, height=4.2)["rate"] == 320.0
    assert quote(front=7.0, height=2.4)["rate"] == 220.0


def test_quote_minimum_lineal_metres():
    q = quote(front=4.0, height=3.0)   # 1.6 + 4.0 + 1.6 = 7.2 lm, below the 10 lm minimum
    assert (q["run"], q["charged"], q["sub"]) == (7.2, 10.0, 2800.0)
