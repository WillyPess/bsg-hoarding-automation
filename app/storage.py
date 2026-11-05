"""Job and run folders in the data folder (PLAN-app.md §7; §11 step 3).

    <data>/jobs/<Job>/job.json            current inputs
                     /<P>_photo.jpg ...   photos
                     /reviews/            AI calls (from §11 step 9)
                     /runs/0001/          one folder per engine run: its own copy of the inputs, the outputs,
                                          engine.json once it has finished
                     /runs/next           the next run number (so a number is never reused)
    <data>/jobs/example-<Name>/           the copy an Example runs on: same layout, its inputs refreshed from
                                          hoarding/<Name> before each run; not in the job list, no real job can use
                                          the name

- Job folder names are the job's prefix, safe on Windows: letters, digits, _ and -, at most 64, starting with a
  letter or digit, not a reserved device name (CON, PRN, AUX, NUL, COM1-9, LPT1-9), and unique ignoring case.
- Run folders are numbered, never reused (a counter in runs/next, checked against the folders and the index), and
  locked once finished: engine.json marks the end, write_run_file refuses to write after it, and the files are made
  read-only on disk as a second lock.
- Every change is recorded in the append-only audit table.
- rebuild_index rebuilds the jobs and runs tables from the folders; the history tables are untouched, and one
  "index.rebuilt" entry is appended to the audit (decided 2026-11-04).

    python -m app.storage rebuild-index      (with the app stopped)"""
import hashlib, json, os, platform, re, shutil, stat, subprocess, sys, time
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from app import db, health

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,127}$")
RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
RUN_DIR = re.compile(r"^\d{4,}$")
EXAMPLE_PREFIX = "example-"
EXAMPLE_INPUTS = ("job.json", "quote_extras.json", "markup.py", "track_plan.py")   # + the photos, not the outputs of a run by hand


class StorageError(ValueError):
    pass


class RunLocked(StorageError):
    """The run has finished: its folder can't be written again."""


@dataclass(frozen=True)
class Run:
    job: str
    number: int
    path: Path


def now():
    return time.time()


# --- names and paths --------------------------------------------------------------------------------------------------

def check_folder_name(name):
    """The name, if it is a safe job folder name on Windows; StorageError otherwise."""
    if not isinstance(name, str) or not NAME.match(name):
        raise StorageError(f"the job folder name must be 1-64 letters, digits, _ or -, starting with a letter or digit, not {name!r}")
    if name.upper() in RESERVED:
        raise StorageError(f"{name!r} is a reserved name on Windows; choose another prefix")
    return name


def _check_file_name(name):
    if not isinstance(name, str) or not FILE.match(name) or ".." in name or name.endswith((".", " ")):
        raise StorageError(f"not a plain file name: {name!r}")
    if name.split(".")[0].upper() in RESERVED:
        raise StorageError(f"{name!r} is a reserved name on Windows")
    return name


def jobs_root(settings):
    return settings.data_dir / "jobs"


def job_dir(settings, folder):
    return jobs_root(settings) / check_folder_name(folder)


def run_dir(settings, folder, number):
    return job_dir(settings, folder) / "runs" / f"{number:04d}"


# --- audit ------------------------------------------------------------------------------------------------------------

def audit(conn, user_id, action, job=None, run=None, **detail):
    """Append one entry to the audit (the database refuses to change or delete it later)."""
    conn.execute("INSERT INTO audit (at, user_id, action, job, run, detail) VALUES (?, ?, ?, ?, ?, ?)",
                 (now(), user_id, action, job, run, json.dumps(detail, ensure_ascii=False, sort_keys=True)))


def user_id(settings, name):
    conn = db.connect(settings)
    try:
        row = conn.execute("SELECT id FROM users WHERE name = ?", (name.strip().lower(),)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise StorageError(f"there is no user called {name!r}")
    return row[0]


# --- jobs -------------------------------------------------------------------------------------------------------------

def _kind(job):
    health._engine_path()
    import validate
    return validate.kind(job)


def _write_json(path, data):
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def create_job(settings, job, user_id):
    """A new job folder jobs/<prefix>/ with job.json, reviews/ and runs/, its index row and an audit entry."""
    folder = check_folder_name(job.get("prefix"))
    if is_example(folder):
        raise StorageError(f"a prefix can't start with {EXAMPLE_PREFIX!r}: that is kept for the Examples")
    root = jobs_root(settings)
    root.mkdir(parents=True, exist_ok=True)
    if any(p.name.lower() == folder.lower() for p in root.iterdir()):
        raise StorageError(f"a job folder called {folder!r} already exists (names are the same ignoring case)")
    conn = db.connect(settings)
    try:
        if conn.execute("SELECT 1 FROM jobs WHERE folder = ?", (folder,)).fetchone():
            raise StorageError(f"a job called {folder!r} already exists")
        d = root / folder
        d.mkdir()                                   # exclusive: fails if it appeared meanwhile
        _write_json(d / "job.json", job)
        (d / "reviews").mkdir(); (d / "runs").mkdir()
        t = now()
        with conn:
            conn.execute("INSERT INTO jobs (folder, prefix, title, site, kind, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (folder, job["prefix"], job.get("title", ""), job.get("site", ""), _kind(job), t, t))
            audit(conn, user_id, "job.created", folder, title=job.get("title", ""), site=job.get("site", ""))
    finally:
        conn.close()
    return d


def is_example(folder):
    return folder.lower().startswith(EXAMPLE_PREFIX)


def example_folder(name):
    return check_folder_name(EXAMPLE_PREFIX + name)


def copy_example(settings, name, source, user_id):
    """Put the inputs of the reference job in source (hoarding/<name>) into its copy in the data folder, as they are
    now, with the index row and an audit entry. Its runs stay. source is only read."""
    folder = example_folder(name)
    job = json.loads((source / "job.json").read_text(encoding="utf-8"))
    d = jobs_root(settings) / folder
    (d / "runs").mkdir(parents=True, exist_ok=True)
    (d / "reviews").mkdir(exist_ok=True)
    for f in d.iterdir():
        if f.is_file():
            f.unlink()
    photos = (f"{job['prefix']}_hoarding_markup.", f"{job['prefix']}_photo.")
    for f in source.iterdir():
        if f.is_file() and (f.name in EXAMPLE_INPUTS or f.name.startswith(photos)):
            shutil.copyfile(f, d / f.name)
    t = now()
    conn = db.connect(settings)
    try:
        with conn:
            conn.execute("""INSERT INTO jobs (folder, prefix, title, site, kind, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT (folder) DO UPDATE SET prefix = excluded.prefix, title = excluded.title, site = excluded.site,
                                                               kind = excluded.kind, updated_at = excluded.updated_at""",
                         (folder, job["prefix"], job.get("title", ""), job.get("site", ""), _kind(job), t, t))
            audit(conn, user_id, "example.copied", folder, source=name)
    finally:
        conn.close()
    return d


def read_job(settings, folder):
    """job.json of a job in the data folder; StorageError when there is no such job."""
    d = job_dir(settings, folder)
    try:
        return json.loads((d / "job.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise StorageError(f"there is no job {folder!r}") from None


def update_job(settings, folder, job, user_id):
    """Replace job.json (the prefix, i.e. the folder, can't change), update its index row and audit the edit."""
    old = read_job(settings, folder)
    if job.get("prefix") != folder:
        raise StorageError(f"the prefix of {folder!r} can't change (it is the job's folder name)")
    changed = sorted(k for k in set(old) | set(job) if old.get(k) != job.get(k))
    _write_json(job_dir(settings, folder) / "job.json", job)
    conn = db.connect(settings)
    try:
        with conn:
            conn.execute("UPDATE jobs SET title = ?, site = ?, kind = ?, updated_at = ? WHERE folder = ?",
                         (job.get("title", ""), job.get("site", ""), _kind(job), now(), folder))
            audit(conn, user_id, "job.edited", folder, changed=changed)
    finally:
        conn.close()
    return changed


def list_jobs(settings, q=""):
    """The job list: index rows with the latest run and whether a run is approved. q filters title or site."""
    conn = db.connect(settings)
    try:
        like = f"%{q.strip().lower()}%"
        return [dict(r) for r in conn.execute(
            """SELECT j.folder, j.title, j.site, j.kind, j.updated_at,
                      (SELECT MAX(number) FROM runs r WHERE r.job = j.folder) AS last_run,
                      (SELECT status FROM runs r WHERE r.job = j.folder ORDER BY number DESC LIMIT 1) AS last_status,
                      (SELECT COALESCE(finished_at, started_at) FROM runs r WHERE r.job = j.folder ORDER BY number DESC LIMIT 1) AS last_at,
                      EXISTS (SELECT 1 FROM runs r WHERE r.job = j.folder AND r.status = 'done') AS has_done,
                      EXISTS (SELECT 1 FROM approvals a WHERE a.job = j.folder) AS approved
               FROM jobs j
               WHERE j.folder NOT LIKE 'example-%' AND (? = '%%' OR lower(j.title) LIKE ? OR lower(j.site) LIKE ?)
               ORDER BY j.updated_at DESC""", (like, like, like))]
    finally:
        conn.close()


def last_summary(settings, folder):
    """run_summary.json of the latest finished run that has one, or {} (the engine's warnings take either)."""
    runs = job_dir(settings, folder) / "runs"
    for r in sorted((p for p in runs.iterdir() if RUN_DIR.match(p.name)) if runs.is_dir() else [], reverse=True):
        f = r / "run_summary.json"
        if (r / "engine.json").exists() and f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
    return {}


def job_history(settings, folder):
    """The audit entries of one job, oldest first, with the user's name."""
    conn = db.connect(settings)
    try:
        return [dict(r) for r in conn.execute(
            "SELECT a.at, a.action, a.run, a.detail, u.name AS user FROM audit a LEFT JOIN users u ON u.id = a.user_id "
            "WHERE a.job = ? ORDER BY a.id", (folder,))]
    finally:
        conn.close()


def write_job_file(settings, folder, name, data):
    """Write a file (e.g. a photo) into the job folder itself: a plain file name, nowhere else."""
    d = job_dir(settings, folder)
    if not d.is_dir():
        raise StorageError(f"there is no job folder {folder!r}")
    path = d / _check_file_name(name)
    path.write_bytes(data)
    return path


def photo_path(settings, folder):
    """Where the marked-up photo of a job is (package_gen's name for it), whether or not it is there yet."""
    from app import photos
    return job_dir(settings, folder) / photos.markup_name(read_job(settings, folder)["prefix"])


def has_photo(settings, folder):
    try:
        return photo_path(settings, folder).is_file()
    except StorageError:
        return False


def save_photo(settings, folder, data, user_id, original_name=""):
    """Store an upload as the job's marked-up photo (photos.prepare: JPG or PNG, upright, as a JPEG), replacing the
    one before. photos.PhotoError when the upload can't be used; then nothing changes. Not for the Examples."""
    from app import photos
    if is_example(folder):
        raise StorageError("the Examples are read-only")
    path = photo_path(settings, folder)
    jpeg, size = photos.prepare(data)
    replaced = path.exists()
    tmp = path.with_name(path.name + ".upload")
    tmp.write_bytes(jpeg)
    os.replace(tmp, path)                       # whole or not at all: a run starting now copies the old or the new one
    conn = db.connect(settings)
    try:
        with conn:
            audit(conn, user_id, "photo.uploaded", folder, replaced=replaced, size=list(size), original=original_name[:200])
    finally:
        conn.close()
    return path


# --- runs -------------------------------------------------------------------------------------------------------------

def _next_number(conn, folder, runs):
    counter = runs / "next"
    n = int(counter.read_text(encoding="utf-8").strip() or 1) if counter.exists() else 1
    on_disk = [int(p.name) for p in runs.iterdir() if p.is_dir() and RUN_DIR.match(p.name)]
    in_index = conn.execute("SELECT MAX(number) FROM runs WHERE job = ?", (folder,)).fetchone()[0] or 0
    return max([n, in_index + 1] + [x + 1 for x in on_disk])


def start_run(settings, folder, user_id):
    """A new run folder with a copy of the job's files (job.json, the photo: the exact inputs of this run)."""
    d = job_dir(settings, folder)
    runs = d / "runs"
    conn = db.connect(settings)
    try:
        n = _next_number(conn, folder, runs)
        while True:
            path = runs / f"{n:04d}"
            try:
                path.mkdir()                        # exclusive: a number is never taken twice
                break
            except FileExistsError:
                n += 1
        (runs / "next").write_text(str(n + 1), encoding="utf-8")
        for f in d.iterdir():
            if f.is_file():
                shutil.copyfile(f, path / f.name)
        with conn:
            conn.execute("INSERT INTO runs (job, number, status, started_at, started_by) VALUES (?, ?, 'running', ?, ?)",
                         (folder, n, now(), user_id))
            audit(conn, user_id, "run.started", folder, n)
    finally:
        conn.close()
    return Run(folder, n, path)


def get_run(settings, folder, number):
    """One run's index row with the name of who started it, or None."""
    runs = _run_rows(settings, folder, number)
    return runs[0] if runs else None


def list_runs(settings, folder):
    """Every run of a job, newest first, with the name of who started it."""
    return _run_rows(settings, folder)


def _run_rows(settings, folder, number=None):
    conn = db.connect(settings)
    try:
        return [dict(r) for r in conn.execute(
            "SELECT r.number, r.status, r.started_at, r.finished_at, r.error, u.name AS who FROM runs r LEFT JOIN users u ON u.id = r.started_by "
            "WHERE r.job = ? AND (? IS NULL OR r.number = ?) ORDER BY r.number DESC", (folder, number, number))]
    finally:
        conn.close()


def running_run(settings, folder):
    """The number of the job's run in progress, or None."""
    conn = db.connect(settings)
    try:
        row = conn.execute("SELECT MAX(number) FROM runs WHERE job = ? AND status = 'running'", (folder,)).fetchone()
    finally:
        conn.close()
    return row[0]


def interrupt_unfinished(settings):
    """At start-up: no worker survives a restart, so a run still marked running was cut off. Its folder stays unfinished."""
    conn = db.connect(settings)
    try:
        with conn:
            for r in conn.execute("SELECT job, number FROM runs WHERE status = 'running'").fetchall():
                conn.execute("UPDATE runs SET status = 'interrupted' WHERE job = ? AND number = ?", (r["job"], r["number"]))
                audit(conn, None, "run.interrupted", r["job"], r["number"])
    finally:
        conn.close()


def is_finished(run):
    return (run.path / "engine.json").exists()


def write_run_file(settings, run, name, data):
    """Write an output into a run that is still running. RunLocked once the run has finished."""
    if is_finished(run):
        raise RunLocked(f"run {run.number:04d} of {run.job} has finished: its files can't be changed")
    path = run.path / _check_file_name(name)
    path.write_bytes(data)
    return path


def engine_info():
    """What produced a run: engine commit, rules.json hash, Python, Pillow and LibreOffice."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        commit = "unknown"
    try:
        pillow = metadata.version("pillow")
    except metadata.PackageNotFoundError:
        pillow = "not installed"
    return {"commit": commit,
            "rules_sha256": hashlib.sha256((ROOT / "hoarding" / "rules.json").read_bytes()).hexdigest(),
            "python": platform.python_version(), "pillow": pillow,
            "libreoffice": health.soffice_path() or "not found"}


def _read_only(path):
    for p in path.rglob("*"):
        if p.is_file():
            p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def finish_run(settings, run, ok, seconds, user_id, error=None):
    """Mark the run finished: engine.json, read-only files, the index row and an audit entry. Only once."""
    if is_finished(run):
        raise RunLocked(f"run {run.number:04d} of {run.job} has already finished")
    t = now()
    info = {**engine_info(), "ok": bool(ok), "seconds": seconds, "error": error,
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))}
    _write_json(run.path / "engine.json", info)
    _read_only(run.path)
    conn = db.connect(settings)
    try:
        with conn:
            conn.execute("UPDATE runs SET status = ?, finished_at = ?, error = ? WHERE job = ? AND number = ?",
                         ("done" if ok else "failed", t, error, run.job, run.number))
            audit(conn, user_id, "run.finished", run.job, run.number, ok=bool(ok), seconds=seconds, error=error)
    finally:
        conn.close()


# --- rebuild-index ----------------------------------------------------------------------------------------------------

def rebuild_index(settings, out=None):
    """Rebuild the jobs and runs tables from the folders. History (audit, approvals, flags, ...) is untouched; one
    "index.rebuilt" entry is appended to the audit. Returns {"jobs": n, "runs": n}. Run it with the app stopped: a run in progress would be marked interrupted."""
    say = out or (lambda msg: None)
    root = jobs_root(settings)
    conn = db.connect(settings)
    n_jobs = n_runs = 0
    try:
        with conn:
            conn.execute("DELETE FROM runs")
            conn.execute("DELETE FROM jobs")
            for d in sorted(root.iterdir() if root.is_dir() else [], key=lambda p: p.name.lower()):
                if not d.is_dir():
                    continue
                try:
                    check_folder_name(d.name)
                    job = json.loads((d / "job.json").read_text(encoding="utf-8"))
                except (StorageError, OSError, ValueError) as e:
                    say(f"skipped {d.name}: {e}")
                    continue
                first = conn.execute("SELECT MIN(at) FROM audit WHERE action = 'job.created' AND job = ?", (d.name,)).fetchone()[0]
                conn.execute("INSERT INTO jobs (folder, prefix, title, site, kind, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (d.name, job.get("prefix", d.name), job.get("title", ""), job.get("site", ""), _kind(job),
                              first or d.stat().st_mtime, (d / "job.json").stat().st_mtime))
                n_jobs += 1
                runs = d / "runs"
                for r in sorted(runs.iterdir() if runs.is_dir() else [], key=lambda p: p.name):
                    if not (r.is_dir() and RUN_DIR.match(r.name)):
                        continue
                    number = int(r.name)
                    started = conn.execute("SELECT at, user_id FROM audit WHERE action = 'run.started' AND job = ? AND run = ?",
                                           (d.name, number)).fetchone()
                    info = None
                    if (r / "engine.json").exists():
                        try:
                            info = json.loads((r / "engine.json").read_text(encoding="utf-8"))
                        except ValueError:
                            info = {"ok": False, "error": "engine.json can't be read"}
                    status = "interrupted" if info is None else ("done" if info.get("ok") else "failed")
                    conn.execute("INSERT INTO runs (job, number, status, started_at, started_by, finished_at, error) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (d.name, number, status, started[0] if started else r.stat().st_mtime, started[1] if started else None,
                                  (r / "engine.json").stat().st_mtime if info is not None else None, (info or {}).get("error")))
                    n_runs += 1
            audit(conn, None, "index.rebuilt", jobs=n_jobs, runs=n_runs)
    finally:
        conn.close()
    return {"jobs": n_jobs, "runs": n_runs}


def main(argv=None):
    from app import settings as S
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["rebuild-index"]:
        print(__doc__)
        return 0 if argv in ([], ["-h"], ["--help"]) else 2
    try:
        st = S.load()
    except S.ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    counts = rebuild_index(st, out=print)
    print(f"Index rebuilt from {jobs_root(st)}: {counts['jobs']} jobs, {counts['runs']} runs. History untouched; the rebuild is in the audit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
