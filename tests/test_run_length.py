"""The quote charges the same run length that the layout, grid sheet and materials form are built from."""
import json, os
from pathlib import Path

import pytest

import baseline, layout_gen
from quotes import quote_gen

STANDARD = {"front": 7.0, "return": 1.6, "height": 4.5, "door_offset": 2.4, "door_width": 1.6}


def job(name):
    return json.loads(Path(os.path.join(baseline.ROOT, "hoarding", name, "job.json")).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", baseline.JOBS)
def test_quote_run_equals_layout_run(name):
    j = job(name)
    assert quote_gen.compute(j)["run"] == layout_gen.runs(j)[4]


def test_unequal_returns_on_a_standard_job_are_refused():
    # Was: quote 1.6 + 7.0 + 1.2 = 9.8 lm, layout/sheet/materials 1.6 + 7.0 + 1.6 = 10.2 m.
    j = {**STANDARD, "right_return": 1.2}
    with pytest.raises(ValueError, match="right_return"):
        layout_gen.faces(j)
    with pytest.raises(ValueError, match="right_return"):
        quote_gen.compute(j)


def test_right_return_equal_to_return_is_accepted():
    j = {**STANDARD, "right_return": 1.6}
    assert quote_gen.compute(j)["run"] == layout_gen.runs(j)[4] == 10.2
