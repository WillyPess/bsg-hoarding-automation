"""v1.1 rule 2 (Gus, 2026-11-01): weights = all uprights, including the 10% spare uprights, x weights per upright from the matrix.
No separate +10% spare weights. External jobs: 8 per upright (rules.json) on all uprights, wind extras and spares included."""
import pytest

import titan


@pytest.mark.parametrize("joints, height, per, weights", [
    (10, 4.5, 7, 77),    # Bikini: 11 uprights x 7
    (14, 4.5, 7, 112),   # FRED_v2: 16 x 7
    (22, 4.5, 7, 175),   # David Jones: 25 x 7
    (18, 4.0, 6, 120),   # Shrungaar: 20 x 6
    (7, 4.2, 6, 48),     # Medibank: 8 x 6
])
def test_weights_are_all_uprights_times_the_matrix(joints, height, per, weights):
    up, wind, spare, p, w = titan.for_job({"height": height}, joints)
    assert (p, w) == (per, weights)


def test_external_weights_on_all_38_uprights():
    # DJ Lift: (24 + 10 wind + 4 spare) x 8 = 304 (v1 sent 34 x 8 x 1.1 = 300)
    assert titan.for_job({"height": 2.4, "external": True}, 24) == (38, 10, 4, 8, 304)


@pytest.mark.parametrize("height", [1.2, 2.4, 3.6, 4.5, 7.2])
def test_no_separate_spare_weights(height):
    for joints in range(1, 60):
        up, wind, spare, per, w = titan.for_job({"height": height}, joints)
        assert w == up * per
