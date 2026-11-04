"""v1.1 rule 3 (Gus, 2026-11-01): anti-tampers = 1 per upright, including the 10% spare uprights
(and the extra wind uprights on external jobs). Replaces v1's 10 per 8.8 m of run.

Checked on the materials form the pipeline writes for every reference job."""
import json, os
from pathlib import Path

import pytest
from openpyxl import load_workbook

import baseline

JOBS = baseline.JOBS


def form_row(xlsx, name):
    ws = load_workbook(xlsx).active
    for row in ws.iter_rows(min_col=2, max_col=4, values_only=True):
        if row[0] == name:
            return row[1], row[2]
    raise AssertionError(f"no {name!r} row on the form")


def prefix(job):
    return json.loads(Path(os.path.join(baseline.ROOT, "hoarding", job, "job.json")).read_text(encoding="utf-8"))["prefix"]


@pytest.mark.parametrize("job", JOBS)
def test_one_anti_tamper_per_upright_sent(job, reference_run):
    summary, work = reference_run(job)
    xlsx = os.path.join(work, f"{prefix(job)}_materials.xlsx")
    tampers, _ = form_row(xlsx, "Anti-Tampers")
    uprights, _ = form_row(xlsx, "Uprights")
    assert tampers == uprights == summary["uprights_to_send"]


def test_spare_and_wind_uprights_get_anti_tampers(reference_run):
    # DJ Lift: 24 at joins + 10 wind + 4 spare = 38 uprights -> 38 anti-tampers (v1: ceil(10 x 24.6 / 8.8) = 28)
    summary, work = reference_run("DavidJonesLift")
    assert form_row(os.path.join(work, f"{prefix('DavidJonesLift')}_materials.xlsx"), "Anti-Tampers")[0] == 38


def test_summary_reports_anti_tampers(reference_run):
    summary, _ = reference_run("FRED_v2")
    assert summary["anti_tampers_to_send"] == summary["uprights_to_send"] == 16
