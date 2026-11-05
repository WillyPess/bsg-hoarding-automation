"""Markers on a job (engenai UI): dust_suppression and ladder are ticks only, with no calculation.

job.json keeps them (with client and drawings_sent_by, shown by the app only). Ticked, each adds a line to the
materials form, below BSG's paper form, with no quantity; nothing else on the form changes. Unticked (or absent),
every reference job's materials form is exactly as in expected/."""
import json, os, subprocess, sys
from pathlib import Path

import pytest

import baseline
import jobs
import validate
from check_fixtures import cells

ROOT = baseline.ROOT
H = os.path.join(ROOT, "hoarding")


def ref(name):
    return json.loads(Path(H, name, "job.json").read_text(encoding="utf-8"))


def materials(job, tmp_path):
    jp, out = tmp_path / "job.json", tmp_path / "m.xlsx"
    jp.write_text(json.dumps(job), encoding="utf-8")
    subprocess.run([sys.executable, os.path.join(H, "materials.py"), str(out), str(jp)], check=True, capture_output=True, cwd=ROOT)
    return cells(out)


def test_normalize_keeps_the_markers_and_the_people():
    j = jobs.normalize({"kind": "standard", "title": "T", "prefix": "T", "site": "Hyperdome", "date": "01/11/2026", "front": 8.0,
                        "height": 4.5, "entry_from": "left", "entry_offset": 1.2, "client": "GPT - Pacific Fair",
                        "drawings_sent_by": "Centre management", "dust_suppression": True, "ladder": True,
                        "extra_doors": 1, "passage_sets": 2, "photo_note": "Camera for centre management"})
    assert (j["client"], j["drawings_sent_by"], j["dust_suppression"], j["ladder"]) == ("GPT - Pacific Fair", "Centre management", True, True)
    assert (j["extra_doors"], j["passage_sets"], j["photo_note"]) == (1, 2, "Camera for centre management")
    assert not validate.check(j)


@pytest.mark.parametrize("key, value", [("extra_doors", -1), ("passage_sets", 1.5), ("ladder", "yes"), ("dust_suppression", 1)])
def test_bad_markers_and_counts_are_refused(key, value):
    assert any(p.field == key for p in validate.check({**ref("Bikini"), key: value}))


@pytest.mark.parametrize("job", baseline.JOBS)
def test_unticked_the_form_is_exactly_as_expected(job, tmp_path):
    j = {**ref(job), "dir": os.path.join(H, job), "dust_suppression": False, "ladder": False}
    want = cells(os.path.join(ROOT, "expected", job, f"{j['prefix']}_materials.xlsx"))
    assert materials(j, tmp_path) == want


@pytest.mark.parametrize("ticks, names", [({"ladder": True}, ["Ladder"]), ({"dust_suppression": True}, ["Dust suppression"]),
                                          ({"ladder": True, "dust_suppression": True}, ["Dust suppression", "Ladder"])])
def test_ticked_adds_a_line_without_quantity(ticks, names, tmp_path):
    j = {**ref("Bikini"), "dir": os.path.join(H, "Bikini")}
    plain, got = materials(j, tmp_path), materials({**j, **ticks}, tmp_path)
    assert {k: v for k, v in got.items() if k in plain} == plain                 # nothing on the paper form changes
    extra = {k: v for k, v in got.items() if k not in plain}
    rows = sorted({r for r, _ in extra})
    assert [extra[(r, 2)] for r in rows if (r, 2) in extra] == names
    for r in rows:
        assert (r, 3) not in extra                                                # no quantity
    assert any("ticked on this job" in str(v).lower() for v in extra.values())
