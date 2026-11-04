"""Job pages (PLAN-app.md §4 screens 2-3; §11 step 4): the job list, Examples, a job's page, the new/edit form.

Every number shown comes from job.json or the engine (warnings); the form's defaults, conversions and checks are
the engine's (jobform.py). Examples are the reference jobs in hoarding/: read-only, so they can't be edited or
approved. Running one works on a copy in the data folder (storage.copy_example; pages_runs.py), never in hoarding/."""
import json, time
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import engine, jobform, storage

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "hoarding"


def _status(row):
    if row["approved"]:
        return "approved"
    return "run" if row["has_done"] else "draft"


def _when(t):
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(t)) if t else ""


def _examples():
    out = []
    for d in sorted(EXAMPLES.iterdir(), key=lambda p: p.name.lower()):
        f = d / "job.json"
        if not f.is_file():
            continue
        try:
            storage.check_folder_name(d.name)
            job = json.loads(f.read_text(encoding="utf-8"))
        except (storage.StorageError, ValueError):
            continue
        if job.get("legacy"):          # the old FRED job, kept for the old scripts: not an example
            continue
        out.append((d.name, job))
    return out


def _example(name):
    for n, job in _examples():
        if n == name:
            return job
    raise HTTPException(status_code=404)


def example_dir(name):
    _example(name)       # 404 unless it is a listed example
    return EXAMPLES / name


def _job_or_404(settings, folder):
    if storage.is_example(folder):      # an Example's copy isn't a job: its pages are under /examples
        raise HTTPException(status_code=404)
    try:
        return storage.read_job(settings, folder)
    except storage.StorageError:
        raise HTTPException(status_code=404) from None


def runs_view(settings, folder):
    return [{**r, "when": _when(r["finished_at"] or r["started_at"])} for r in storage.list_runs(settings, folder)]


def add_routes(app, page, settings):
    def form_page(request, values, problems, mode, folder=None, status_code=200):
        return page(request, "job_form.html", status_code, v=values, problems=problems, mode=mode, folder=folder,
                    sites=jobform.SITES, labels=jobform.LABELS, defaults=engine.RULES["defaults"],
                    kiosk_door=engine.RULES["kiosk_door"]["leaf_height"],
                    suggestion=engine.suggest_prefix(values.get("title") or "") if values.get("title") else "")

    @app.get("/jobs", response_class=HTMLResponse)
    def job_list(request: Request, q: str = ""):
        rows = []
        for r in storage.list_jobs(settings, q):
            kind = r["kind"]
            try:
                job = storage.read_job(settings, r["folder"])
                n_warn = len(engine.warnings(job, storage.last_summary(settings, r["folder"])))
                if job.get("kiosk"):
                    kind = "kiosk"     # a kiosk is a standard-shaped job with "kiosk": true (rule 7)
            except storage.StorageError:
                n_warn = None
            rows.append({**r, "kind": kind, "status": _status(r), "last_at_text": _when(r["last_at"]), "warnings": n_warn})
        return page(request, "jobs.html", rows=rows, q=q, tab="jobs")

    @app.get("/jobs/new", response_class=HTMLResponse)
    def new_job_form(request: Request):
        return form_page(request, jobform.blank(request.state.user), {}, "new")

    @app.post("/jobs/new", response_class=HTMLResponse)
    async def new_job_save(request: Request):
        user = request.state.user
        v, job, problems = jobform.process(await request.form(), user)
        if job is not None:
            try:
                storage.create_job(settings, job, user.id)
            except storage.StorageError as e:
                job, problems = None, {"prefix": [str(e)]}
        if job is None:
            return form_page(request, v, problems, "new", status_code=422)
        return RedirectResponse(f"/jobs/{job['prefix']}", status_code=303)

    @app.get("/jobs/{folder}", response_class=HTMLResponse)
    def job_page(request: Request, folder: str):
        job = _job_or_404(settings, folder)
        history = [{**h, "when": _when(h["at"]), "detail": json.loads(h["detail"] or "{}")} for h in storage.job_history(settings, folder)]
        warnings = engine.warnings(job, storage.last_summary(settings, folder))
        return page(request, "job.html", job=job, folder=folder, kind=engine.kind(job), warnings=warnings,
                    history=history, labels=jobform.LABELS, runs=runs_view(settings, folder), base=f"/jobs/{folder}")

    def _editable(job):
        return engine.kind(job) == "standard"

    @app.get("/jobs/{folder}/edit", response_class=HTMLResponse)
    def edit_job_form(request: Request, folder: str):
        job = _job_or_404(settings, folder)
        if not _editable(job):
            return page(request, "job_not_editable.html", job=job, folder=folder, kind=engine.kind(job))
        return form_page(request, jobform.from_job(job), {}, "edit", folder)

    @app.post("/jobs/{folder}/edit", response_class=HTMLResponse)
    async def edit_job_save(request: Request, folder: str):
        old = _job_or_404(settings, folder)
        if not _editable(old):
            raise HTTPException(status_code=409, detail=f"A {engine.kind(old)} job can't be edited here yet.")
        user = request.state.user
        v, job, problems = jobform.process(await request.form(), user, prefix=folder, by=old.get("by") or user.name, keep=old)
        if job is None:
            return form_page(request, v, problems, "edit", folder, status_code=422)
        storage.update_job(settings, folder, job, user.id)
        return RedirectResponse(f"/jobs/{folder}", status_code=303)

    @app.get("/examples", response_class=HTMLResponse)
    def example_list(request: Request):
        rows = [{"name": n, "title": j.get("title", n), "site": j.get("site", ""), "kind": "kiosk" if j.get("kiosk") else engine.kind(j)}
                for n, j in _examples()]
        return page(request, "examples.html", rows=rows, tab="examples")

    @app.get("/examples/{name}", response_class=HTMLResponse)
    def example_page(request: Request, name: str):
        job = _example(name)
        return page(request, "example.html", job=job, example=name, kind=engine.kind(job),
                    labels=jobform.LABELS, runs=runs_view(settings, storage.example_folder(name)), base=f"/examples/{name}")
