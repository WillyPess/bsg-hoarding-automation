"""Rounding traps: counts that are "rounded up" must not jump by one on floating-point noise."""
from decimal import Decimal

import layout_gen, titan
from quotes import quote_gen


def test_weights_50_x_1_1_is_55():
    # 10 uprights x 5 weights (3.6 m row) x 1.1 = 55.00000000000001 in floating point
    assert 10 * 5 * 1.1 > 55
    assert titan.counterweights(10, 3.6) == (5, 55)
    assert titan.for_job({"height": 3.6}, 10) == (11, 0, 1, 5, 55)   # + 1 spare upright (rule 1); weights on the 10 until rule 2


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
    # DJ Lift: 24 x 0.4 = 9.6 -> 10 extra uprights; 34 x 0.1 = 3.4 -> 4 spare (38); 34 x 8 x 1.1 = 299.2 -> 300 weights
    assert titan.for_job({"height": 2.4, "extra_uprights": 0.4, "weights_per_upright": 8}, 24) == (38, 10, 4, 8, 300)


def quote(**job):
    return quote_gen.compute({"return": 1.6, "door_offset": 1.0, **job})


def test_quote_height_band_at_exact_limits():
    assert quote(front=7.0, height=4.2)["rate"] == 320.0
    assert quote(front=7.0, height=2.4)["rate"] == 220.0


def test_quote_minimum_lineal_metres():
    q = quote(front=4.0, height=3.0)   # 1.6 + 4.0 + 1.6 = 7.2 lm, below the 10 lm minimum
    assert (q["run"], q["charged"], q["sub"]) == (7.2, 10.0, 2800.0)


def test_quote_gst_half_cent_rounds_up():
    # 10.125 lm x $330 = $3,341.25; GST 334.125 -> 334.13 (float round gave 334.12)
    q = quote(front=6.925, height=4.8)
    assert (q["charged"], q["sub"], q["gst"], q["total"]) == (10.125, Decimal("3341.25"), Decimal("334.13"), Decimal("3675.38"))


def test_quote_line_half_cent_rounds_up():
    # Kiosk: 15.011 lm x $115 = $1,726.265 -> 1,726.27 (float round gave 1,726.26)
    q = quote(front=11.811, height=1.2, kiosk=True)
    assert (q["charged"], q["lines"][0][4], q["gst"], q["total"]) == (15.011, Decimal("1726.27"), Decimal("172.63"), Decimal("1898.90"))


def test_quote_extras_in_cents():
    # Extra lines from job.json (float rates/quantities) are added in exact cents; POA lines stay out of the total.
    q = quote(front=7.0, height=3.0, extra_doors=1, passage_sets=3,
              extra_lines=[{"desc": "a", "qty": 3, "rate": 0.1}, {"desc": "b", "qty": 1, "rate": None}])
    # 10.2 lm x $280 = 2,856.00 + 400.00 + 150.00 + 0.30 = 3,406.30; GST 340.63
    assert (q["sub"], q["gst"], q["total"]) == (Decimal("3406.30"), Decimal("340.63"), Decimal("3746.93"))
