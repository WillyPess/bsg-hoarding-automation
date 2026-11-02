"""v1.1 rule 7 (Gus, 2026-11-01, CLAUDE.md §3, §4, §12), assumptions approved 2026-11-02:
  - a 1.2 m kiosk ("kiosk": true) uses 2400 x 1200 sheets laid horizontally (2.4 m long x 1.2 m high), no cut, no tops;
    joints and uprights every 2.4 m at most (weight matrix for 1.2 m: 2.4 m centres, 2 per upright);
  - the entry is 1.6 x 1.2 m: leaves 0.8 x 1.2 m, one normal door cut in half, so the form lists 1 door;
  - the 4 x 2.3 m door studs stay, with a warning in the package (on the boss's list);
  - validate refuses "kiosk": true unless the height is exactly 1.2 m (any other: ask Gus);
  - a 1.2 m job without "kiosk": true gets a warning asking whether it is a kiosk (it changes the rate);
  - Pacific Fair quote: $115/lm, 15 lm minimum."""
import json, os, shutil

import pytest
from openpyxl import load_workbook

import baseline, jobs, layout_gen, run_job, tape, validate
from check_fixtures import pdf_text


def kiosk():
    return json.load(open(os.path.join(baseline.ROOT, "hoarding", "Kiosk_PF", "job.json")))


def test_sheets_laid_horizontally():
    c = layout_gen.compute(kiosk())
    assert (c["kiosk"], c["sheet_w"], c["sheet_h"], c["panel_h"], c["cut_off"], c["tops"], c["door"]) == (True, 2.4, 1.2, 1.2, 0, 0, None)
    assert len(c["full"]) == 1                                  # front left: one whole 2400 sheet
    assert sorted(cu["w"] for b in c["bins"] for cu in b["cuts"]) == [1.6, 1.6, 2.0]
    assert c["sheets"] == 4
    assert layout_gen.cut_offs(c) == []


def test_uprights_at_the_joins_every_2_4_m_at_most():
    c = layout_gen.compute(kiosk())
    assert c["uprights"] == [0.0, 1.6, 4.0, 5.6, 7.6, 9.2]
    assert max(b - a for a, b in zip(c["uprights"], c["uprights"][1:])) <= 2.4


def test_tape_joints():
    j = kiosk()
    t = tape.white_tape(j, layout_gen.compute(j))
    assert (t["vertical_joints"], t["vertical_mm"], t["tops_mm"], t["door_mm"], t["rolls"]) == (6, 7200, 0, 4000, 1)


def test_standard_jobs_keep_1200_wide_sheets():
    j = json.load(open(os.path.join(baseline.ROOT, "hoarding", "Bikini", "job.json")))
    c = layout_gen.compute(j)
    assert (c["kiosk"], c["sheet_w"]) == (False, 1.2)
    assert layout_gen.compute(kiosk())["sheet_w"] == 2.4 and layout_gen.compute(j)["sheet_w"] == 1.2   # no leftover between jobs


def test_helpers_do_not_keep_the_kiosk_width():
    # after a kiosk job, the standalone helpers still count standard 1.2 m sheets (no module state leaks into them)
    layout_gen.compute(kiosk())
    assert layout_gen.nfull(21.6) == 18
    assert layout_gen.ffd([{"x": 0, "w": 1.0}])[0]["left"] == 0.2
    assert layout_gen.nfull(21.6, 2.4) == 9


@pytest.mark.parametrize("height", [1.0, 1.8, 2.4])
def test_validate_kiosk_only_at_1_2_m(height):
    j = {**kiosk(), "height": height, "door_height": min(1.0, height)}
    [p] = [p for p in validate.check(j) if p.field == "height"]
    assert "1.2" in p.message and "Gus" in p.message


def test_validate_kiosk_at_1_2_m():
    assert validate.check(kiosk()) == []


def test_warning_for_1_2_m_without_kiosk():
    j = {**kiosk()}; del j["kiosk"]
    assert validate.check(j) == []                               # allowed, but flagged
    ws = [w for w in jobs.warnings(j, {}) if "kiosk" in w.message.lower()]
    assert ws and "rate" in ws[0].message and ws[0].rule == "CLAUDE.md §12"
    assert not [w for w in jobs.warnings(kiosk(), {}) if "is it a kiosk" in w.message.lower()]


def test_warning_for_kiosk_door_studs():
    ws = [w for w in jobs.warnings(kiosk(), {}) if w.rule == "door_set.studs_short_length"]
    assert len(ws) == 1 and "kiosk" in ws[0].message


def test_normalize_kiosk_entry_defaults_to_1_2_m():
    i = {k: v for k, v in kiosk().items() if k not in ("dir", "door_offset", "door_height", "door_width", "return")}
    j = jobs.normalize({**i, "kind": "standard", "entry_from": "left", "entry_offset": 2.4})
    assert (j["door_height"], j["door_width"]) == (1.2, 1.6)


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    work = str(tmp_path_factory.mktemp("k") / "Kiosk_PF")
    shutil.copytree(os.path.join(baseline.ROOT, "hoarding", "Kiosk_PF"), work)
    return run_job.run(work), work


def rows(work):
    ws = load_workbook(os.path.join(work, "Kiosk_PF_materials.xlsx")).active
    return {r[0]: (r[1], r[2]) for r in ws.iter_rows(min_col=2, max_col=4, values_only=True) if r[0]}


def test_form_lists_1_door_cut_in_half(run):
    _, work = run
    r = rows(work)
    assert r["Doors"] == (1, "2340 cut in half: 2 leaves 800 x 1200")
    assert r["16mm Melamine"] == ("6 x", "2.4m laid horizontally (+2 spare)")


def test_summary(run):
    s, _ = run
    assert (s["layout_sheets"], s["sheets_to_send"], s["uprights_to_send"], s["weights_per_upright"], s["weights_to_send"]) == (4, 6, 7, 2, 14)
    assert (s["white_tape_rolls"], s["black_tape_rolls"], s["tops"], s["cut_offs_to_tops_stock"]) == (1, 1, 0, "")


def test_quote_kiosk_rate_and_15_lm_minimum(run):
    s, _ = run
    assert (s["run_m"], s["quote_lm"], s["quote_rate"], s["quote_ex_gst"], s["quote_gst"], s["quote_total"]) == (9.2, 15, 115, 1725.0, 172.5, 1897.5)


def test_package_doors_and_stud_warning(run):
    _, work = run
    text = " ".join(pdf_text(os.path.join(work, "Kiosk_PF_Hoarding_Package.pdf"))[1])
    assert "one 2340 door cut in half" in text.lower() and "800 x 1200" in text
    assert "2.3 m door studs" in text and "1.2 m kiosk" in text
    assert "laid horizontally" in text
