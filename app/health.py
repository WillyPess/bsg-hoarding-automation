"""Health checks for the health page and `python -m app --check`: can the app and the engine work on this PC?
Each check is (name, ok, detail, level): level "ok", "warn" (shown, but the app still works: e.g. no recent backup)
or "fail" (ok is False). Nothing here computes a hoarding quantity."""
import os, sys, tempfile, time
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOARDING = os.path.join(ROOT, "hoarding")


BACKUP_MAX_AGE = 2 * 86400   # the health page warns when the last backup is older (PLAN-app.md §7)


def now():
    return time.time()


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    level: str = field(default="")

    def __post_init__(self):
        if not self.level:
            object.__setattr__(self, "level", "ok" if self.ok else "fail")


def _engine_path():
    if HOARDING not in sys.path:
        sys.path.insert(0, HOARDING)


def soffice_path():
    """LibreOffice binary as the engine finds it (paths.soffice), or None when it isn't installed."""
    _engine_path()
    import paths
    p = paths.soffice()
    return p if p and os.path.exists(p) else None


def font_paths():
    _engine_path()
    import paths
    return [paths.F, paths.FB]


def checks(settings):
    out = []
    # data folder: exists and writable
    try:
        with tempfile.NamedTemporaryFile(dir=settings.data_dir, prefix=".health-", delete=True):
            pass
        out.append(Check("Data folder", True, str(settings.data_dir)))
    except OSError as e:
        out.append(Check("Data folder", False, f"{settings.data_dir}: not writable ({e.strerror or e})"))
    out.append(Check("config.toml", settings.config_path.is_file(), str(settings.config_path)))
    # engine rules: rules.json loads (the values the engine uses)
    try:
        _engine_path()
        from rules import RULES
        out.append(Check("Engine rules", True, f"rules.json: {len(RULES)} sections"))
    except Exception as e:   # shown on the page, not raised: the page must still load
        out.append(Check("Engine rules", False, f"rules.json can't be loaded: {e}"))
    lo = soffice_path()
    out.append(Check("LibreOffice", bool(lo), lo or "not found: the materials PDF needs LibreOffice (set SOFFICE or install it)"))
    missing = [p for p in font_paths() if not os.path.exists(p)]
    out.append(Check("Fonts", not missing, "DejaVu fonts found" if not missing else "missing: " + ", ".join(missing)))
    out.append(backup_check(settings))
    return out


def backup_check(settings):
    """A warning, never a failure: the app works without backups, but Gus must see that they are missing."""
    from app import backup
    if settings.backup_dir is None:
        return Check("Backup", True, "No backup folder set: add [backup] folder to config.toml and register the daily task (README).", "warn")
    last = backup.last_backup(settings)
    if not last:
        return Check("Backup", True, f"No backup yet in {settings.backup_dir}: run python -m app.backup, or check the daily task (README).", "warn")
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(last["at"]))
    if now() - last["at"] > BACKUP_MAX_AGE:
        return Check("Backup", True, f"The last backup is more than 2 days old ({when}, {last['folder']}): check the daily task.", "warn")
    return Check("Backup", True, f"Last backup {when}: {last['folder']}")
