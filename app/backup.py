"""Daily backup of the data folder (PLAN-app.md §7; §11 step 3).

    python -m app.backup

Copies the data folder into <backup folder>/BSG-YYYY-MM-DD_HHMMSS/ (the folder is set in config.toml, [backup]).
The database is copied through SQLite's backup API, so the copy is one consistent file even while the app writes.
Backups older than 30 days are deleted; only folders this script made (BSG-<date>) are ever touched. The time of
the last backup is kept in <data folder>/last_backup.json and in the audit; the health page warns when there is
no backup folder or the last backup is more than 2 days old. Run daily by a Windows scheduled task (README)."""
import json, os, re, shutil, sqlite3, stat, sys, time
from contextlib import closing
from pathlib import Path

from app import db, storage

KEEP_DAYS = 30
PREFIX = "BSG-"
STAMP = "%Y-%m-%d_%H%M%S"
OURS = re.compile(r"^BSG-(\d{4}-\d{2}-\d{2}_\d{6})(\.partial)?$")
SQLITE_FILES = ("bsg.sqlite", "bsg.sqlite-wal", "bsg.sqlite-shm", "bsg.sqlite-journal")


class BackupError(Exception):
    pass


def _skipper(data_dir):
    """What copytree must not copy: the live database and its WAL files at the top of the data folder (the database
    is copied through the backup API instead), and the health check's temporary files."""
    top = Path(data_dir).resolve()
    def skip(directory, names):
        here = Path(directory).resolve() == top
        return [n for n in names if (here and n in SQLITE_FILES) or n.startswith(".health-")]
    return skip


def _force_remove(path):
    """rmtree that also removes read-only files (finished runs are read-only; Windows refuses to delete them)."""
    def retry(func, p, _exc):
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        func(p)
    shutil.rmtree(path, onexc=retry) if sys.version_info >= (3, 12) else shutil.rmtree(path, onerror=retry)


def last_backup(settings):
    """{"at": epoch seconds, "folder": path} of the last backup, or None."""
    try:
        return json.loads((settings.data_dir / "last_backup.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def prune(root, keep_days=KEEP_DAYS, now=None):
    """Delete our backups (BSG-<date>, and half-made .partial ones) older than keep_days. Never anything else."""
    limit = (now or time.time()) - keep_days * 86400
    removed = []
    for p in root.iterdir():
        m = OURS.match(p.name)
        if not (m and p.is_dir()):
            continue
        try:
            made = time.mktime(time.strptime(m.group(1), STAMP))
        except ValueError:
            continue
        if made < limit:
            _force_remove(p)
            removed.append(p.name)
    return removed


def run(settings):
    """Make one backup, prune the old ones and record it in the audit. Returns the new backup folder."""
    final = make_copy(settings)
    removed = prune(settings.backup_dir)
    conn = db.connect(settings)
    try:
        with conn:
            storage.audit(conn, None, "backup.done", folder=str(final), removed=removed)
    finally:
        conn.close()
    return final


def make_copy(settings):
    """Copy the data folder (the database through SQLite's backup API: only committed data, one consistent file),
    then write last_backup.json. Returns the new backup folder."""
    root = settings.backup_dir
    if root is None:
        raise BackupError("No backup folder is set: add it to config.toml, [backup] folder = 'D:\\BSG-backups'")
    root.mkdir(parents=True, exist_ok=True)
    t = time.time()
    while (root / (PREFIX + time.strftime(STAMP, time.localtime(t)))).exists():
        t += 1
    name = PREFIX + time.strftime(STAMP, time.localtime(t))
    partial, final = root / (name + ".partial"), root / name
    try:
        shutil.copytree(settings.data_dir, partial, ignore=_skipper(settings.data_dir))
        src = db.connect(settings)
        try:
            with closing(sqlite3.connect(partial / "bsg.sqlite")) as dst:
                src.backup(dst)
        finally:
            src.close()
        partial.rename(final)
    except Exception as e:
        if partial.exists():
            _force_remove(partial)
        raise BackupError(f"backup failed: {e}") from e
    (settings.data_dir / "last_backup.json").write_text(json.dumps({"at": time.time(), "folder": str(final)}), encoding="utf-8")
    return final


def main():
    from app import settings as S
    try:
        st = S.load()
        target = run(st)
    except (BackupError, S.ConfigError) as e:
        print(f"Backup not done: {e}", file=sys.stderr)
        return 1
    print(f"Backup done: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
