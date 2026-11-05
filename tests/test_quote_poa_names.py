"""run_job.counts(): the quote's POA lines by name (quote_poa_names), the engine's own text from quote_gen's lines.

The results page lists them ("Wind loading ...: POA") instead of a count. No PDF or count changes."""
import json, os
from pathlib import Path

import baseline
import run_job

WIND = "Wind loading for external install: 10 extra uprights (34 in total) and 8 counterweights per upright"


def job(name):
    d = os.path.join(baseline.ROOT, "hoarding", name)
    j = json.loads(Path(d, "job.json").read_text(encoding="utf-8"))
    j["dir"] = d
    return j


def test_dj_lift_names_its_wind_line():
    s = run_job.counts(job("DavidJonesLift"))
    assert s["quote_poa_names"] == [WIND]
    assert s["quote_poa_lines"] == len(s["quote_poa_names"])


def test_names_are_the_quote_lines_text(monkeypatch):
    j = {**job("FRED_v2"), "extra_lines": [{"desc": "Public holiday work", "rate": None}, {"desc": "Paint", "qty": 2, "rate": 10},
                                           {"desc": "Oversized transport", "rate": None}]}
    s = run_job.counts(j)
    assert s["quote_poa_names"] == ["Public holiday work", "Oversized transport"]     # in quote order, priced lines left out
    assert s["quote_poa_lines"] == 2


def test_no_poa_lines_is_an_empty_list():
    assert run_job.counts(job("FRED_v2"))["quote_poa_names"] == []


def test_no_quote_off_pacific_fair():
    assert "quote_poa_names" not in run_job.counts(job("Bikini"))
