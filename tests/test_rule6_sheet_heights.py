"""v1.1 rule 6 (Gus, 2026-11-01, CLAUDE.md §4): melamine comes only 2400 x 1200 and 3600 x 1200.
  - height up to 2.4 m: 2400 sheets, no tops;
  - over 2.4 up to 3.6 m: 3600 sheets cut down to the hoarding height; the cut-offs go to tops stock, not waste;
  - over 3.6 m: 3600 sheets + tops.
The engine picks the sheet from the height (rules.json sheet.heights); job.json "sheet_h" still overrides it."""
import json, os, subprocess, sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

import baseline, layout_gen, tape


def bikini(height, **kw):
    j = json.loads(Path(os.path.join(baseline.ROOT, "hoarding", "Bikini", "job.json")).read_text(encoding="utf-8"))
    j.update(height=height, **kw)
    return j


@pytest.mark.parametrize("height, sheet", [(1.8, 2.4), (2.4, 2.4), (2.41, 3.6), (3.0, 3.6), (3.6, 3.6), (4.5, 3.6), (7.2, 3.6)])
def test_sheet_by_height_band(height, sheet):
    assert layout_gen.sheet_for(height) == sheet


def test_job_sheet_h_still_overrides():
    j = bikini(3.0, sheet_h=2.4)
    assert layout_gen.compute(j)["sheet_h"] == 2.4


def test_3_0_m_cuts_3600_sheets_down():
    c = layout_gen.compute(bikini(3.0))
    assert (c["sheet_h"], c["panel_h"], c["cut_off"], c["tops"]) == (3.6, 3.0, 0.6, 0)
    assert c["sheets"] == 9                                   # same 9 sheets as at 4.5 m
    assert c["door"]["h"] == 0.6                              # door top from 2400 to 3000, not 1200 high
    assert layout_gen.cut_offs(c) == [(1200, 600, 8)]         # S1-S8 cut down; the door sheet S9 is turned, no cut-off
    assert layout_gen.tops_to_cut(bikini(3.0), c) == []


def test_2_4_m_uses_2400_sheets_with_no_door_top():
    c = layout_gen.compute(bikini(2.4))
    assert (c["sheet_h"], c["panel_h"], c["cut_off"], c["tops"], c["door"]) == (2.4, 2.4, 0, 0, None)
    assert c["sheets"] == 8
    assert layout_gen.cut_offs(c) == []


def test_3_6_m_exactly_full_sheets_no_tops():
    c = layout_gen.compute(bikini(3.6))
    assert (c["sheet_h"], c["panel_h"], c["cut_off"], c["tops"]) == (3.6, 3.6, 0, 0)


def test_above_3_6_m_unchanged():
    c = layout_gen.compute(bikini(4.5))
    assert (c["sheet_h"], c["panel_h"], c["cut_off"], c["tops"], c["door"]["h"]) == (3.6, 3.6, 0, 8, 1.2)


def test_no_tops_joint_when_cut_down():
    j = bikini(3.0)
    assert tape.white_tape(j, layout_gen.compute(j))["tops_mm"] == 0


def run_materials(tmp_path, job):
    p = tmp_path / "job.json"; p.write_text(json.dumps(job))
    out = tmp_path / "m.xlsx"
    subprocess.run([sys.executable, os.path.join(baseline.ROOT, "hoarding", "materials.py"), str(out), str(p)], check=True, capture_output=True)
    ws = load_workbook(out).active
    return next(r for r in ws.iter_rows(min_col=2, max_col=4, values_only=True) if r[0] == "16mm Melamine")


def test_form_says_cut_down_and_cut_offs(tmp_path):
    assert run_materials(tmp_path, bikini(3.0))[1:] == ("11 x", "3.6m cut to 3.0m (+2 spare)   Cut-offs to tops stock: 8 x 1200 x 600")


def test_form_2400_sheets(tmp_path):
    assert run_materials(tmp_path, bikini(2.4))[1:] == ("10 x", "2.4m (+2 spare)")


def test_layout_draws_at_3_0_m(tmp_path):
    out = tmp_path / "l.png"
    layout_gen.render(bikini(3.0), str(out))
    assert out.exists()
