"""Engine runs in the background (PLAN-app.md, Demo scope, PR A), so the page can say "running..." meanwhile.

One engine run at a time, across all jobs: LibreOffice can't convert two files at once with one profile. A run waiting
its turn shows as running too. One app process, so plain locks are enough. A run in progress when the app stops is
marked interrupted at the next start (storage.interrupt_unfinished)."""
import threading, time

from app import engine, storage

_starting = threading.Lock()     # the check and the start are one step: a double click doesn't start two runs of a job
_engine = threading.Lock()


def start(settings, folder, user_id, prepare=None):
    """Start a run of the job and return its number; the run already in progress, if there is one. prepare() runs
    just before a new run starts (an Example's copy, which must not change while another run of it is starting)."""
    with _starting:
        number = storage.running_run(settings, folder)
        if number is not None:
            return number
        if prepare:
            prepare()
        run = storage.start_run(settings, folder, user_id)
    threading.Thread(target=_work, args=(settings, run, user_id), daemon=True).start()
    return run.number


def _work(settings, run, user_id):
    with _engine:
        t = time.monotonic()
        try:
            error = engine.run_job(run.path)
        except Exception as e:           # the run must end as failed, not stay "running" for ever
            error = f"{type(e).__name__}: {e}"
        storage.finish_run(settings, run, error is None, round(time.monotonic() - t, 1), user_id, error)
