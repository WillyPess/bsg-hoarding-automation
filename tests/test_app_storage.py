"""Storage (PLAN-app.md §7; §11 step 3): the data folder layout, the SQLite schema, the append-only audit, run folders
that are numbered, never reused and locked once finished, safe job folder names, WAL mode, rebuild-index, and the
daily backup with its health warning."""
import hashlib, json, os, sqlite3, stat, subprocess, sys, time
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app_helpers as H
from app import backup, db, health, settings as S, storage, users


@pytest.fixture
def data(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def s(data):
    st = S.load(data)
    users.add(st, "gus", "estimator", H.PASSWORD)
    return st


@pytest.fixture
def gus(s):
    return storage.user_id(s, "gus")


JOB = json.loads((Path(H.ROOT) / "hoarding" / "Bikini" / "job.json").read_text(encoding="utf-8"))


def job(prefix="Bikini", **kw):
    j = {**JOB, "prefix": prefix, **kw}
    j.pop("dir", None)
    return j


def raw(s):
    """A plain sqlite3 connection, not the app's: the database itself must enforce the rules."""
    return closing(sqlite3.connect(s.data_dir / "bsg.sqlite"))


# --- settings ---------------------------------------------------------------------------------------------------------

def test_backup_folder_setting_is_empty_by_default(data):
    st = S.load(data)
    assert st.backup_dir is None
    assert '[backup]\nfolder = ""' in (data / "config.toml").read_text(encoding="utf-8").replace("\r", "")


def test_older_config_without_backup_section_still_loads(data):
    data.mkdir(parents=True)
    (data / "config.toml").write_text('[server]\nport = 8000\n', encoding="utf-8")
    assert S.load(data).backup_dir is None


def test_backup_folder_set(data, tmp_path):
    data.mkdir(parents=True)
    (data / "config.toml").write_text(f'[backup]\nfolder = "{(tmp_path / "backups").as_posix()}"\n', encoding="utf-8")
    assert S.load(data).backup_dir == tmp_path / "backups"


@pytest.mark.parametrize("folder, word", [("relative/folder", "full path"), (None, "inside the data folder")])
def test_bad_backup_folder(data, folder, word):
    data.mkdir(parents=True)
    folder = folder or (data / "backups").as_posix()
    (data / "config.toml").write_text(f'[backup]\nfolder = "{folder}"\n', encoding="utf-8")
    with pytest.raises(S.ConfigError, match=word):
        S.load(data)


# --- schema -----------------------------------------------------------------------------------------------------------

TABLES = {"users", "sessions", "login_attempts", "jobs", "runs", "approvals", "flags", "escalations", "ai_calls", "audit"}


def test_schema(s):
    with raw(s) as c:
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert TABLES <= names
        assert c.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
        for t in ("flags", "escalations", "ai_calls"):                # the AI tables stay empty until §11 steps 9-12
            assert c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0


def test_a_step_2_database_is_upgraded_and_keeps_its_users(data):
    data.mkdir(parents=True)
    st = S.load(data)
    with closing(sqlite3.connect(data / "bsg.sqlite")) as c:          # build the step-2 database by hand
        c.executescript(db.MIGRATIONS[0]); c.execute("PRAGMA user_version = 1")
        c.execute("INSERT INTO users (name, role, password_hash, created_at) VALUES ('gus', 'estimator', 'x', 0)"); c.commit()
    db.connect(st).close()
    with raw(st) as c:
        assert c.execute("SELECT name FROM users").fetchall() == [("gus",)]
        assert c.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)


def test_wal_mode(s):
    with raw(s) as c:
        assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_a_running_job_does_not_block_the_pages(s, gus):
    storage.create_job(s, job(), gus)
    writer = db.connect(s)
    try:
        writer.execute("BEGIN IMMEDIATE")                            # e.g. a run in progress writing its rows
        writer.execute("INSERT INTO audit (at, user_id, action) VALUES (?, ?, 'test.write')", (time.time(), gus))
        reader = db.connect(s)                                       # a page reading at the same time
        try:
            t = time.time()
            assert reader.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
            assert time.time() - t < 1
        finally:
            reader.close()
    finally:
        writer.rollback(); writer.close()


# --- audit: append-only -----------------------------------------------------------------------------------------------

def test_audit_is_append_only_in_the_database_itself(s, gus):
    storage.create_job(s, job(), gus)
    with raw(s) as c:
        n = c.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        assert n >= 1
        c.execute("INSERT INTO audit (at, user_id, action) VALUES (1, NULL, 'test.append')"); c.commit()
        for sql in ("UPDATE audit SET action = 'changed'", "DELETE FROM audit", "DELETE FROM audit WHERE id = 1"):
            with pytest.raises(sqlite3.DatabaseError, match="append-only"):
                c.execute(sql)
        assert c.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == n + 1


def test_audit_records_who_and_what(s, gus):
    storage.create_job(s, job(), gus)
    with raw(s) as c:
        row = c.execute("SELECT user_id, action, job, run, detail FROM audit WHERE action = 'job.created'").fetchone()
    assert row[:4] == (gus, "job.created", "Bikini", None)
    assert json.loads(row[4])["title"] == JOB["title"]


# --- job folders ------------------------------------------------------------------------------------------------------

def test_job_folder_layout(s, gus):
    d = storage.create_job(s, job(), gus)
    assert d == s.data_dir / "jobs" / "Bikini"
    assert json.loads((d / "job.json").read_text(encoding="utf-8")) == job()
    assert (d / "reviews").is_dir() and (d / "runs").is_dir()
    with raw(s) as c:
        assert c.execute("SELECT folder, prefix, title, site, kind FROM jobs").fetchall() == \
            [("Bikini", "Bikini", JOB["title"], "Hyperdome", "standard")]


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "a\\b", "../x", "C:x", "a b", "x.", "é", "a" * 65,
                                  "CON", "con", "Prn", "AUX", "NUL", "COM1", "com9", "LPT1", "lpt9", "-x", "_x"])
def test_unsafe_folder_names(name):
    with pytest.raises(storage.StorageError):
        storage.check_folder_name(name)


@pytest.mark.parametrize("name", ["Bikini", "FRED_v2", "DavidJonesLift", "Kiosk_PF", "CONSOLE", "COM10", "a", "a" * 64])
def test_safe_folder_names(name):
    assert storage.check_folder_name(name) == name


def test_folder_names_are_unique_ignoring_case(s, gus):
    storage.create_job(s, job("Bikini"), gus)
    for other in ("bikini", "BIKINI", "Bikini"):
        with pytest.raises(storage.StorageError, match="already"):
            storage.create_job(s, job(other), gus)


def test_folder_unique_even_if_only_on_disk(s, gus):
    (s.data_dir / "jobs" / "fred").mkdir(parents=True)              # a folder copied in by hand, not in the index yet
    with pytest.raises(storage.StorageError, match="already"):
        storage.create_job(s, job("FRED"), gus)


def test_job_files_stay_inside_the_job_folder(s, gus):
    storage.create_job(s, job(), gus)
    storage.write_job_file(s, "Bikini", "Bikini_photo.jpg", b"jpg")
    assert (s.data_dir / "jobs" / "Bikini" / "Bikini_photo.jpg").read_bytes() == b"jpg"
    for bad in ("../x.jpg", "runs/0001/x", "..\\x", "/etc/x", "C:\\x", "reviews/../../x"):
        with pytest.raises(storage.StorageError):
            storage.write_job_file(s, "Bikini", bad, b"x")


# --- run folders ------------------------------------------------------------------------------------------------------

def test_run_folders_are_numbered(s, gus):
    storage.create_job(s, job(), gus)
    r1, r2 = storage.start_run(s, "Bikini", gus), storage.start_run(s, "Bikini", gus)
    assert (r1.number, r1.path.name, r2.number, r2.path.name) == (1, "0001", 2, "0002")
    assert json.loads((r1.path / "job.json").read_text(encoding="utf-8")) == job()   # the exact inputs of this run
    with raw(s) as c:
        assert c.execute("SELECT job, number, status, started_by FROM runs ORDER BY number").fetchall() == \
            [("Bikini", 1, "running", gus), ("Bikini", 2, "running", gus)]


def test_run_numbers_are_never_reused(s, gus):
    storage.create_job(s, job(), gus)
    storage.start_run(s, "Bikini", gus); r2 = storage.start_run(s, "Bikini", gus)
    import shutil
    shutil.rmtree(r2.path)                                          # someone deletes run 0002 by hand
    with raw(s) as c:
        c.execute("DELETE FROM runs WHERE number = 2"); c.commit()  # and its index row
    assert storage.start_run(s, "Bikini", gus).number == 3


def test_finish_run_writes_engine_json(s, gus):
    storage.create_job(s, job(), gus)
    r = storage.start_run(s, "Bikini", gus)
    storage.write_run_file(s, r, "run_summary.json", b"{}")
    storage.finish_run(s, r, ok=True, seconds=4.2, user_id=gus)
    e = json.loads((r.path / "engine.json").read_text(encoding="utf-8"))
    rules = (Path(H.ROOT) / "hoarding" / "rules.json").read_bytes()
    assert e["rules_sha256"] == hashlib.sha256(rules).hexdigest()
    assert e["ok"] is True and e["seconds"] == 4.2 and e["finished_at"]
    assert {"commit", "python", "pillow", "libreoffice"} <= set(e)
    with raw(s) as c:
        assert c.execute("SELECT status FROM runs").fetchone()[0] == "done"
        assert [a for (a,) in c.execute("SELECT action FROM audit ORDER BY id")] == ["job.created", "run.started", "run.finished"]


@pytest.mark.parametrize("ok, status", [(True, "done"), (False, "failed")])
def test_a_finished_run_cannot_be_written_again(s, gus, ok, status):
    storage.create_job(s, job(), gus)
    r = storage.start_run(s, "Bikini", gus)
    storage.write_run_file(s, r, "Bikini_melamine_layout.png", b"png")
    storage.finish_run(s, r, ok=ok, seconds=1.0, user_id=gus, error=None if ok else "engine said no")
    with pytest.raises(storage.RunLocked):
        storage.write_run_file(s, r, "Bikini_melamine_layout.png", b"changed")
    with pytest.raises(storage.RunLocked):
        storage.write_run_file(s, r, "new.txt", b"new")
    with pytest.raises(storage.RunLocked):
        storage.finish_run(s, r, ok=True, seconds=1.0, user_id=gus)
    assert (r.path / "Bikini_melamine_layout.png").read_bytes() == b"png"
    for f in r.path.iterdir():                                       # read-only on disk as well (second lock)
        assert not f.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH), f.name
    with raw(s) as c:
        assert c.execute("SELECT status FROM runs").fetchone()[0] == status


def test_run_files_stay_inside_the_run_folder(s, gus):
    storage.create_job(s, job(), gus)
    r = storage.start_run(s, "Bikini", gus)
    for bad in ("../job.json", "..\\x", "/x", "sub/x"):
        with pytest.raises(storage.StorageError):
            storage.write_run_file(s, r, bad, b"x")


# --- rebuild-index ----------------------------------------------------------------------------------------------------

def index_rows(s):
    with raw(s) as c:
        return (c.execute("SELECT folder, prefix, title, site, kind FROM jobs ORDER BY folder").fetchall(),
                c.execute("SELECT job, number, status FROM runs ORDER BY job, number").fetchall())


def history(s):
    with raw(s) as c:
        return {t: c.execute(f"SELECT * FROM {t} ORDER BY id").fetchall() for t in ("audit", "approvals")}


def make_jobs(s, gus):
    storage.create_job(s, job("Bikini"), gus)
    storage.create_job(s, job("FRED_v2", title="FRED", site="Pacific Fair"), gus)
    a = storage.start_run(s, "Bikini", gus); storage.finish_run(s, a, ok=True, seconds=1, user_id=gus)
    b = storage.start_run(s, "Bikini", gus); storage.finish_run(s, b, ok=False, seconds=1, user_id=gus, error="x")
    storage.start_run(s, "FRED_v2", gus)                            # never finished: the app stopped mid-run
    with raw(s) as c:
        c.execute("INSERT INTO approvals (job, run, user_id, at, note) VALUES ('Bikini', 1, ?, 1, 'ok')", (gus,)); c.commit()


def test_rebuild_index_from_the_folders(s, gus):
    make_jobs(s, gus)
    jobs_before, runs_before = index_rows(s)
    hist = history(s)
    with raw(s) as c:
        c.execute("DELETE FROM runs"); c.execute("DELETE FROM jobs"); c.commit()   # the index is lost
    counts = storage.rebuild_index(s)
    jobs_after, runs_after = index_rows(s)
    assert jobs_after == jobs_before
    assert runs_after == [("Bikini", 1, "done"), ("Bikini", 2, "failed"), ("FRED_v2", 1, "interrupted")]
    assert runs_before[:2] == runs_after[:2]
    after = history(s)
    assert after["approvals"] == hist["approvals"]                  # untouched
    assert after["audit"][:-1] == hist["audit"]                     # every earlier entry as it was ...
    last = after["audit"][-1]                                        # ... plus one "index rebuilt" entry (decided 2026-11-04)
    assert last[3] == "index.rebuilt" and json.loads(last[6]) == {"jobs": 2, "runs": 3}
    assert counts == {"jobs": 2, "runs": 3}


def test_rebuild_index_picks_up_a_job_copied_in_by_hand(s, gus):
    d = s.data_dir / "jobs" / "Medibank"
    d.mkdir(parents=True)
    (d / "job.json").write_text(json.dumps(job("Medibank", title="Medibank - Pacific Fair")), encoding="utf-8")
    (s.data_dir / "jobs" / "notes").mkdir()                         # a folder without job.json is skipped
    storage.rebuild_index(s)
    assert [r[0] for r in index_rows(s)[0]] == ["Medibank"]


def test_rebuild_index_cli(s, gus):
    make_jobs(s, gus)
    env = {**os.environ, "BSG_DATA": str(s.data_dir)}
    r = subprocess.run([sys.executable, "-m", "app.storage", "rebuild-index"], cwd=H.ROOT, env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "2 jobs" in r.stdout and "3 runs" in r.stdout


# --- backup -----------------------------------------------------------------------------------------------------------

@pytest.fixture
def sb(data, tmp_path):
    """Settings with a backup folder, a user and a job."""
    data.mkdir(parents=True)
    (data / "config.toml").write_text(f'[backup]\nfolder = "{(tmp_path / "backups").as_posix()}"\n', encoding="utf-8")
    st = S.load(data)
    users.add(st, "gus", "estimator", H.PASSWORD)
    storage.create_job(st, job(), storage.user_id(st, "gus"))
    return st


def test_backup_copies_the_data_folder(sb):
    target = backup.run(sb)
    assert target.parent == sb.backup_dir and target.name.startswith("BSG-")
    assert (target / "config.toml").is_file()
    assert (target / "jobs" / "Bikini" / "job.json").is_file()
    assert not list(target.glob("bsg.sqlite-*"))                    # no -wal / -shm: the backup API gives one whole file
    with closing(sqlite3.connect(target / "bsg.sqlite")) as c:
        assert c.execute("SELECT name FROM users").fetchall() == [("gus",)]
        assert c.execute("SELECT COUNT(*) FROM audit WHERE action = 'job.created'").fetchone()[0] == 1


def test_backup_includes_committed_data_while_a_write_is_open(sb):
    w = db.connect(sb)
    try:
        w.execute("BEGIN IMMEDIATE")
        w.execute("INSERT INTO audit (at, action) VALUES (1, 'not.committed')")
        target = backup.make_copy(sb)                                # the copy only; run() then records it in the audit
    finally:
        w.rollback(); w.close()
    with closing(sqlite3.connect(target / "bsg.sqlite")) as c:
        assert c.execute("SELECT COUNT(*) FROM audit WHERE action = 'not.committed'").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM audit WHERE action = 'job.created'").fetchone()[0] == 1


def test_backup_records_the_time(sb):
    backup.run(sb)
    last = backup.last_backup(sb)
    assert last and abs(last["at"] - time.time()) < 60 and Path(last["folder"]).is_dir()
    with raw(sb) as c:
        assert c.execute("SELECT COUNT(*) FROM audit WHERE action = 'backup.done'").fetchone()[0] == 1


def test_backup_keeps_30_days(sb, monkeypatch):
    sb.backup_dir.mkdir(parents=True)
    old = sb.backup_dir / time.strftime("BSG-%Y-%m-%d_%H%M%S", time.localtime(time.time() - 31 * 86400))
    recent = sb.backup_dir / time.strftime("BSG-%Y-%m-%d_%H%M%S", time.localtime(time.time() - 29 * 86400))
    other = sb.backup_dir / "Photos 2025"                            # not ours: never touched
    for d in (old, recent, other):
        d.mkdir()
    backup.run(sb)
    assert not old.exists() and recent.exists() and other.exists()


def test_backup_without_a_folder(s):
    with pytest.raises(backup.BackupError, match="folder"):
        backup.run(s)


def test_backup_cli(sb, s=None):
    env = {**os.environ, "BSG_DATA": str(sb.data_dir)}
    r = subprocess.run([sys.executable, "-m", "app.backup"], cwd=H.ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "BSG-" in r.stdout


def test_backup_cli_without_a_folder(data):
    S.load(data)
    env = {**os.environ, "BSG_DATA": str(data)}
    r = subprocess.run([sys.executable, "-m", "app.backup"], cwd=H.ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "backup" in r.stderr.lower()


# --- health: backup warnings ------------------------------------------------------------------------------------------

def backup_check(st):
    [c] = [c for c in health.checks(st) if c.name == "Backup"]
    return c


def test_health_warns_when_no_backup_folder_is_set(s):
    c = backup_check(s)
    assert c.level == "warn" and c.ok and "no backup folder" in c.detail.lower()


def test_health_warns_when_there_is_no_backup_yet(sb):
    c = backup_check(sb)
    assert c.level == "warn" and "no backup yet" in c.detail.lower()


def test_health_ok_after_a_backup(sb):
    backup.run(sb)
    assert backup_check(sb).level == "ok"


def test_health_warns_when_the_last_backup_is_older_than_2_days(sb, monkeypatch):
    backup.run(sb)
    t = time.time()
    monkeypatch.setattr(health, "now", lambda: t + 2 * 86400 + 60)
    c = backup_check(sb)
    assert c.level == "warn" and "2 days" in c.detail


def test_health_page_shows_the_warning_without_failing(s):
    app = H.make_app(s.data_dir, people=(("boss", "manager"),))[0]
    c = H.logged_in(app, "boss")
    r = c.get("/health.json")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    [b] = [x for x in r.json()["checks"] if x["name"] == "Backup"]
    assert b["level"] == "warn"
    page = c.get("/health")
    assert page.status_code == 200 and "WARN" in page.text
