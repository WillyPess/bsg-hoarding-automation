"""The app's only door into the engine (PLAN-app.md §1, §6): the engine's own functions, imported from hoarding/.

The input side: jobs.normalize (form inputs -> job.json, defaults from rules.json), validate.check (what is wrong),
jobs.warnings and jobs.suggest_prefix. Running it: run_job, the same `python run_job.py <folder>` as by hand, in its
own process. No app module imports the calculators (layout_gen, titan, tape, materials, ...): every number comes from
the engine."""
import locale, os, subprocess, sys
from pathlib import Path

from app import health

health._engine_path()
import jobs as _jobs        # noqa: E402  hoarding/jobs.py
import validate as _validate  # noqa: E402  hoarding/validate.py
from rules import RULES     # noqa: E402  hoarding/rules.json (read-only here: shown as hints, never applied by the app)

if health.ROOT not in sys.path:
    sys.path.insert(0, health.ROOT)
import run_job as _run_job   # noqa: E402  run_job.counts: the engine's key numbers, the same as run_summary.json

normalize = _jobs.normalize
suggest_prefix = _jobs.suggest_prefix
warnings = _jobs.warnings
check = _validate.check
kind = _validate.kind
Problem = _validate.Problem

RUN_TIMEOUT = 300    # seconds: a stuck LibreOffice must not hold the other runs back for ever
ERROR_TAIL = 4000    # characters of the engine's output shown when a run fails


def estimate(job, folder):
    """The key numbers of a job.json not saved yet (the form's bottom bar): run_job.counts, in this process, with
    no files written. folder = where the job would live (for its quote_extras.json, if any). None when the engine
    can't work it out from these inputs (the form then says what is wrong)."""
    try:
        return _run_job.counts({**job, "dir": str(folder)})
    except Exception:      # half-typed inputs: the bar shows dashes, the save says what is wrong
        return None


def run_job(folder, timeout=RUN_TIMEOUT):
    """Run the engine on a folder holding job.json and the photo: the outputs land there, what it prints in engine.log.
    Returns None when it worked, otherwise what the engine said."""
    log = Path(folder) / "engine.log"
    try:
        with open(log, "wb") as f:   # a file, not a pipe: a stuck child can't block the timeout (Windows)
            done = subprocess.run([sys.executable, os.path.join(health.ROOT, "run_job.py"), str(folder)], cwd=health.ROOT,
                                  stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"The engine didn't finish in {timeout:g} s and was stopped."
    if done.returncode == 0:
        return None
    said = log.read_text(encoding=locale.getencoding(), errors="replace").strip()   # Python prints to a file in the locale's encoding
    return said[-ERROR_TAIL:] or f"The engine stopped with exit code {done.returncode}."


__all__ = ["normalize", "suggest_prefix", "warnings", "check", "kind", "Problem", "RULES", "run_job", "estimate"]
