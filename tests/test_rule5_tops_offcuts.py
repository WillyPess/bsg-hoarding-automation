"""v1.1 rule 5 (Gus, 2026-11-01): the form lists only how many tops to cut from offcuts, with their sizes.
Tops are not counted as new sheets; the person loading the truck adds a sheet per top size not in stock.
The piece above the entry comes from the door sheet (already in the sheet count), so it is not an offcut top."""
import json, os

import pytest
from openpyxl import load_workbook

import baseline, layout_gen


def job(name):
    return json.load(open(os.path.join(baseline.ROOT, "hoarding", name, "job.json")))


@pytest.mark.parametrize("name, want", [
    ("Bikini", [(1200, 900, 7), (400, 900, 1)]),
    ("FRED_v2", [(1200, 900, 9), (1000, 900, 1), (400, 900, 2)]),
    ("Shrungaar", [(1200, 400, 14), (1000, 400, 1), (100, 400, 1)]),
    ("Medibank", [(1200, 600, 7), (1100, 600, 1), (600, 600, 1), (400, 600, 1)]),
    ("DavidJonesLift", []),   # 2.4 m on 2400 sheets: no tops
])
def test_tops_to_cut_are_pieces_with_sizes(name, want):
    j = job(name)
    assert layout_gen.tops_to_cut(j, layout_gen.compute(j)) == want


def form(name, work):
    ws = load_workbook(os.path.join(work, f"{job(name)['prefix']}_materials.xlsx")).active
    return next(r for r in ws.iter_rows(min_col=2, max_col=4, values_only=True) if r[0] == "16mm Melamine")


def test_form_lists_tops_from_offcuts_not_as_sheets(reference_run):
    summary, work = reference_run("Bikini")
    name, qty, desc = form("Bikini", work)
    assert qty == "11 x"   # 9 layout + 2 spare, no sheets for the tops
    assert desc == "3.6m (+2 spare)   Tops from offcuts: 7 x 1200 x 900 + 1 x 400 x 900"
    assert summary["tops_from_offcuts"] == "7 x 1200 x 900 + 1 x 400 x 900"


def test_no_tops_line_without_tops(reference_run):
    summary, work = reference_run("DavidJonesLift")
    assert form("DavidJonesLift", work)[2] == "2.4m (+2 spare)"
    assert summary["tops_from_offcuts"] == ""
