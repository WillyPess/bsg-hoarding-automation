"""What the screens show, as text (the engenai UI): formatting of the engine's numbers, run status, audit entries.

Every number comes from a run's run_summary.json (or job.json for an input such as the height), shown as it is: the
only arithmetic here is adding up the summaries on the dashboard. Nothing here computes a hoarding quantity."""
import time
from decimal import Decimal


def when(t):
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(t)) if t else ""


def num(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


def money(v):
    """$7,656 for whole dollars, $3,341.25 otherwise."""
    if v is None:
        return "—"
    d = Decimal(str(v))
    return f"${d:,.0f}" if d == d.to_integral_value() else f"${d:,.2f}"


def metres(v, unit="m"):
    return "—" if v is None else f"{num(v)} {unit}"


def example_name(folder):
    return folder[len("example-"):] if folder.lower().startswith("example-") else None


def job_url(folder):
    name = example_name(folder)
    return f"/examples/{name}" if name else f"/jobs/{folder}"


def status(running, latest_run, done):
    """{key, label, run, number}: running > the latest run failed > PDFs ready > no PDFs yet."""
    if running is not None:
        return {"key": "running", "label": "Generating PDFs", "run": "running", "number": running}
    if latest_run and latest_run["status"] in ("failed", "interrupted"):
        return {"key": "failed", "label": "Run failed", "run": latest_run["status"], "number": latest_run["number"]}
    if done:
        return {"key": "done", "label": "PDFs ready", "run": "done", "number": done[0]}
    return {"key": "draft", "label": "No PDFs yet", "run": "none", "number": None}


HIDDEN = {"run.started"}      # "PDFs generated (vN)" says it; the start is in the run's own page


def describe(a):
    """An audit entry in words: (what, note)."""
    act, d, run = a["action"], a.get("detail") or {}, a.get("run")
    v = f" (v{run})" if run else ""
    text = {
        "login": "Signed in",
        "job.created": "Job created",
        "example.copied": "Example copied to run it",
        "job.edited": "Job edited",
        "job.corrected": "Job fixed",
        "photo.uploaded": "Photo replaced" if d.get("replaced") else "Photo uploaded",
        "run.started": f"PDFs requested{v}",
        "run.interrupted": f"Run interrupted{v}",
        "file.downloaded": f"Downloaded {d.get('file', '')}".strip(),
        "backup.done": "Backup done",
        "index.rebuilt": "Index rebuilt",
    }.get(act)
    if act == "run.finished":
        text = f"PDFs generated{v}" if d.get("ok") else f"Run failed{v}"
    return text or act, d.get("note") or ""
