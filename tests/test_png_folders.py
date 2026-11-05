"""Drawing baselines per OS: a run is compared with the folder for the OS it runs on, and only that folder is written."""
import os

import pytest

import baseline
import test_reference_jobs as R
import update_baseline


@pytest.mark.parametrize("name", ["linux", "windows"])
def test_folder_follows_the_os(name, monkeypatch):
    monkeypatch.setattr(baseline, "OS", name)
    assert baseline.png_dir("Bikini") == os.path.join(baseline.ROOT, "expected", "Bikini", "png", name)


def test_no_folder_for_this_os_says_so_with_the_command(monkeypatch, tmp_path):
    monkeypatch.setattr(baseline, "OS", "otheros")
    with pytest.raises(AssertionError) as e:
        R.check_drawings("Bikini", str(tmp_path))
    message = str(e.value)
    assert "No stored drawings for Bikini on otheros" in message
    assert os.path.join("Bikini", "png", "otheros") in message
    assert "python tests/update_baseline.py --store-pngs Bikini" in message


@pytest.fixture
def stores(monkeypatch, tmp_path):
    """A job with one image stored for each OS, this OS being windows, and a new image in the work folder."""
    monkeypatch.setattr(baseline, "ROOT", str(tmp_path))
    monkeypatch.setattr(baseline, "OS", "windows")
    png = tmp_path / "expected" / "Job" / "png"
    for name in ("linux", "windows"):
        (png / name).mkdir(parents=True)
        (png / name / "a.png").write_bytes(name.encode())
    work = tmp_path / "work"
    work.mkdir()
    (work / "a.png").write_bytes(b"new")
    return png, str(work)


def test_store_writes_only_to_this_os(stores):
    png, work = stores
    update_baseline.store("Job", work, ["a.png"])
    assert (png / "windows" / "a.png").read_bytes() == b"new"
    assert (png / "linux" / "a.png").read_bytes() == b"linux"


def test_store_with_nothing_to_store_leaves_the_folder_alone(stores, monkeypatch):
    # --store-pngs when no drawing matches the hash: what is stored stays, and no empty folder appears for a new OS
    png, work = stores
    update_baseline.store("Job", work, [])
    assert (png / "windows" / "a.png").read_bytes() == b"windows"
    monkeypatch.setattr(baseline, "OS", "otheros")
    update_baseline.store("Job", work, [])
    assert not (png / "otheros").exists()
