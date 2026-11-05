"""Job pages (engenai UI): the job list (jobs and the Examples), New job, a job's page, Fix job, and the form's bar.

Every number shown comes from a run's run_summary.json or job.json, as it is; the form's defaults, conversions and
checks are the engine's (jobform.py); the form's bottom bar asks the engine too (engine.estimate). Examples are the
reference jobs in hoarding/: read-only, so they can't be fixed or approved. Running one works on a copy in the data
folder (storage.copy_example; pages_runs.py), never in hoarding/."""
import json

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from app import engine, jobform, photos, runner, storage, views
from app.health import ROOT
from pathlib import Path

EXAMPLES = Path(ROOT) / "hoarding"
_when = views.when


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


def _kind(job):
    return "kiosk" if job.get("kiosk") else engine.kind(job)


def _state(settings, folder):
    """(latest finished run or None, status) of a job folder."""
    done = storage.latest_done(settings, folder)
    runs = storage.list_runs(settings, folder)
    return done, views.status(storage.running_run(settings, folder), runs[0] if runs else None, done)


def entry(settings, folder, job, people, example=None, updated=None):
    """One row of the job list."""
    done, st = _state(settings, folder)
    s = done[2] if done else {}
    return {"folder": folder, "url": f"/examples/{example}" if example else f"/jobs/{folder}", "example": example,
            "title": job.get("title") or folder, "site": job.get("site", ""), "client": job.get("client", ""), "kind": _kind(job),
            "height": views.metres(job.get("height")), "run": views.metres(s.get("run_m"), "lm"),
            "quote": views.money(s["quote_ex_gst"]) if "quote_ex_gst" in s else "—",
            "created_by": people.get(folder), "sent_by": job.get("drawings_sent_by", ""), "status": st, "summary": s,
            "finished_at": done[1] if done else None, "touched": max(done[1] if done else 0, updated or 0)}


def all_entries(settings):
    """Every job, then every Example (with its copy's runs), as list rows."""
    people = storage.creators(settings)
    rows = []
    for r in storage.list_jobs(settings):
        try:
            job = storage.read_job(settings, r["folder"])
        except storage.StorageError:
            job = {"title": r["title"], "site": r["site"]}
        rows.append(entry(settings, r["folder"], job, people, updated=r["updated_at"]))
    for name, job in _examples():
        rows.append(entry(settings, storage.example_folder(name), job, people, example=name))
    return sorted(rows, key=lambda r: -r["touched"])        # latest first; Examples never run, last (in name order)


def _estimate_view(job, e):
    return {"run": views.metres(e.get("run_m"), "lm"), "entry": f"{job['door_offset']:.2f} m",
            "ladder": "Yes" if job.get("ladder") else "No", "weights": views.num(e.get("weights_per_upright")),
            "quote": views.money(e["quote_ex_gst"]) if "quote_ex_gst" in e else "—"}


def add_routes(app, page, settings):
    from app import pages_runs as PR       # the results tables (imports this module too)

    def form_page(request, values, problems, mode, folder=None, status_code=200):
        photo_url = ""
        if folder and storage.has_photo(settings, folder):
            photo_url = f"/jobs/{folder}/photo?v={int(storage.photo_path(settings, folder).stat().st_mtime)}"
        return page(request, "job_form.html", status_code, v=values, problems=problems, mode=mode, folder=folder,
                    sites=jobform.SITES, labels=jobform.LABELS, defaults=engine.RULES["defaults"], photo_url=photo_url,
                    kiosk_door=engine.RULES["kiosk_door"]["leaf_height"], tab="new" if mode == "new" else "jobs",
                    suggestion=engine.suggest_prefix(values.get("title") or "") if values.get("title") else "")

    async def read_photo(form, problems):
        """The uploaded photo's bytes, or None when no file was chosen; a photo the engine can't use is a problem."""
        up = form.get("photo")
        if up is None or isinstance(up, str) or not getattr(up, "filename", ""):
            return None, ""
        data = await up.read(photos.MAX_BYTES + 1)
        try:
            photos.prepare(data)
        except photos.PhotoError as e:
            problems.setdefault("photo", []).append(str(e))
        return data, up.filename

    # --- the job list ---------------------------------------------------------------------------------------------

    @app.get("/jobs", response_class=HTMLResponse)
    def job_list(request: Request, q: str = "", site: str = "", who: str = ""):
        rows = all_entries(settings)
        sites = sorted({r["site"] for r in rows if r["site"]})
        people = sorted({r["created_by"] for r in rows if r["created_by"]})
        words = q.strip().lower()
        if words:
            rows = [r for r in rows if words in " ".join(str(r[k] or "") for k in ("title", "folder", "site", "client", "created_by", "sent_by")).lower()]
        if site:
            rows = [r for r in rows if r["site"] == site]
        if who:
            rows = [r for r in rows if r["created_by"] == who]
        return page(request, "jobs.html", rows=rows, q=q, site=site, who=who, sites=sites, people=people, tab="jobs")

    @app.get("/examples")
    def examples():
        return RedirectResponse("/jobs", status_code=303)      # the Examples are in the job list now

    # --- new job --------------------------------------------------------------------------------------------------

    @app.get("/jobs/new", response_class=HTMLResponse)
    def new_job_form(request: Request):
        return form_page(request, jobform.blank(request.state.user), {}, "new")

    @app.post("/jobs/new", response_class=HTMLResponse)
    async def new_job_save(request: Request):
        user = request.state.user
        form = await request.form()
        v, job, problems = jobform.process(form, user)
        data, name = await read_photo(form, problems)
        if problems:
            job = None
        if job is not None:
            try:
                storage.create_job(settings, job, user.id)
            except storage.StorageError as e:
                job, problems = None, {"prefix": [str(e)]}
        if job is None:
            return form_page(request, v, problems, "new", status_code=422)
        folder = job["prefix"]
        if data is not None:
            storage.save_photo(settings, folder, data, user.id, name)
            runner.start(settings, folder, user.id)          # Generate PDFs: with the photo, the run starts at once
        return RedirectResponse(f"/jobs/{folder}", status_code=303)

    @app.post("/jobs/estimate")
    async def estimate(request: Request):
        """The form's bottom bar: the engine's numbers for what is typed so far (nothing is saved). Before a title, a
        site or a date is filled in, stand-ins are used for those only, so the sizes can be shown already."""
        form = await request.form()
        f = {k: form.get(k) for k in form.keys() if k != "photo"}
        if not str(f.get("title") or "").strip():
            f["title"] = "Estimate"
        if not str(f.get("site") or "").strip() or (f.get("site") == "other" and not str(f.get("site_other") or "").strip()):
            f["site"], f["site_other"] = "other", "(not chosen yet)"
        if not str(f.get("date") or "").strip():
            f["date"] = jobform.blank(request.state.user)["date"]
        f.pop("prefix", None)
        _, job, _ = jobform.process(f, request.state.user)
        if job is None:
            return JSONResponse({"ladder": "Yes" if form.get("ladder") is not None else "No"})
        e = engine.estimate(job, storage.jobs_root(settings) / job["prefix"])
        if e is None:
            return JSONResponse({"ladder": "Yes" if job.get("ladder") else "No"})
        return JSONResponse(_estimate_view(job, e))

    # --- a job's page ---------------------------------------------------------------------------------------------

    def render_job(request, folder, job, base, example=None, status_code=200, photo_error=""):
        done, st = _state(settings, folder)
        summary = done[2] if done else storage.last_summary(settings, folder)
        number = done[0] if done else None
        stats, drawings, downloads, materials, quote = [], [], [], [], []
        if done:
            path = storage.run_dir(settings, folder, number)
            run_job = PR._read_json(path / "job.json") or job
            s = summary
            if "sheets_to_send" in s and "layout_sheets" in s:
                sheets = f"{s['layout_sheets']} + {s['sheets_to_send'] - s['layout_sheets']}"     # the engine's two numbers
            else:
                sheets = views.num(s.get("sheets_to_send", "—"))
            stats = [{"key": "run_m", "label": "Run (lm)", "value": views.num(s.get("run_m", "—"))},
                     {"key": "sheets", "label": "Sheets", "value": sheets},
                     {"key": "tops", "label": "Tops", "value": views.num(s.get("tops", "—"))},
                     {"key": "uprights", "label": "Uprights", "value": views.num(s.get("uprights_to_send", "—"))},
                     {"key": "weights", "label": "Weights", "value": views.num(s.get("total_weights_to_send", "—"))}]
            files = f"{base}/runs/{number}/files"
            drawings = [(label, f"{files}/{name}") for label, name in PR._drawings(run_job) if (path / name).is_file()]
            P = run_job["prefix"]
            for label, name, title in [("Hoarding Package PDF", f"{P}_Hoarding_Package.pdf", ""),
                                       (f"Quotation · {views.money(s.get('quote_ex_gst'))}", run_job.get("quote_file", f"{P}_Quotation.pdf"), "ex GST"),
                                       ("Materials form (PDF)", f"{P}_materials.pdf", ""), ("Materials form (Excel)", f"{P}_materials.xlsx", "")]:
                if (path / name).is_file():
                    downloads.append({"label": label, "url": f"{files}/{name}", "title": title})
            materials, quote = PR._rows(PR.MATERIALS, s), PR._quote_rows(s)
        history = []
        for h in storage.job_history(settings, folder):
            a = {**h, "detail": json.loads(h["detail"] or "{}")}
            if a["action"] in views.HIDDEN:
                continue
            text, note = views.describe(a)
            history.append({"text": text, "note": note, "user": a["user"], "when": _when(a["at"]),
                            "changed": a["detail"].get("changed") if a["action"] in ("job.edited", "job.corrected") else None,
                            "run_url": f"{base}/runs/{a['run']}" if a["run"] and a["action"] == "run.finished" else ""})
        if example:
            has_photo = (EXAMPLES / example / photos.markup_name(job["prefix"])).is_file()
            photo_v = 0
        else:
            has_photo = storage.has_photo(settings, folder)
            photo_v = int(storage.photo_path(settings, folder).stat().st_mtime) if has_photo else 0   # a replaced photo isn't shown from the cache
        return page(request, "job.html", status_code, job=job, folder=folder, base=base, example=example, kind=_kind(job),
                    status=st, version=number, stats=stats, drawings=drawings, downloads=downloads, materials=materials, quote=quote,
                    warnings=engine.warnings(job, summary), history=history, labels=jobform.LABELS,
                    created_by=storage.creators(settings).get(folder), editable=not example and engine.kind(job) == "standard",
                    has_photo=has_photo, can_run=has_photo, photo_v=photo_v, photo_error=photo_error,
                    max_mb=photos.MAX_BYTES // (1024 * 1024), tab="jobs")

    @app.get("/jobs/{folder}", response_class=HTMLResponse)
    def job_page(request: Request, folder: str):
        return render_job(request, folder, _job_or_404(settings, folder), f"/jobs/{folder}")

    @app.post("/jobs/{folder}/photo", response_class=HTMLResponse)
    async def upload_photo(request: Request, folder: str):
        job = _job_or_404(settings, folder)
        up = (await request.form()).get("photo")
        if up is None or isinstance(up, str) or not getattr(up, "filename", ""):
            return render_job(request, folder, job, f"/jobs/{folder}", status_code=422, photo_error="Choose the marked-up photo (JPG or PNG) first.")
        data = await up.read(photos.MAX_BYTES + 1)
        try:
            storage.save_photo(settings, folder, data, request.state.user.id, up.filename)
        except photos.PhotoError as e:
            return render_job(request, folder, job, f"/jobs/{folder}", status_code=e.status, photo_error=str(e))
        return RedirectResponse(f"/jobs/{folder}", status_code=303)

    @app.get("/jobs/{folder}/photo")
    def show_photo(folder: str):
        _job_or_404(settings, folder)
        path = storage.photo_path(settings, folder)
        if not path.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(path, media_type="image/jpeg")

    # --- Fix job --------------------------------------------------------------------------------------------------

    def _editable(job):
        return engine.kind(job) == "standard"

    @app.get("/jobs/{folder}/edit", response_class=HTMLResponse)
    def edit_job_form(request: Request, folder: str):
        job = _job_or_404(settings, folder)
        if not _editable(job):
            return page(request, "job_not_editable.html", job=job, folder=folder, kind=engine.kind(job), tab="jobs")
        return form_page(request, {**jobform.from_job(job), "note": ""}, {}, "fix", folder)

    @app.post("/jobs/{folder}/edit", response_class=HTMLResponse)
    async def edit_job_save(request: Request, folder: str):
        old = _job_or_404(settings, folder)
        if not _editable(old):
            raise HTTPException(status_code=409, detail=f"A {engine.kind(old)} job can't be fixed here yet.")
        user = request.state.user
        form = await request.form()
        v, job, problems = jobform.process(form, user, prefix=folder, by=old.get("by") or user.name, keep=old)
        v["note"] = note = str(form.get("note") or "").strip()
        if not note:
            problems["note"] = ["say what was wrong: it is kept in the job's history"]
        data, name = await read_photo(form, problems)
        if problems:
            return form_page(request, v, problems, "fix", folder, status_code=422)
        storage.update_job(settings, folder, job, user.id, note=note)
        if data is not None:
            storage.save_photo(settings, folder, data, user.id, name)
        if storage.has_photo(settings, folder):
            runner.start(settings, folder, user.id)          # the next version, recorded as a correction
        return RedirectResponse(f"/jobs/{folder}", status_code=303)

    # --- Examples -------------------------------------------------------------------------------------------------

    @app.get("/examples/{name}", response_class=HTMLResponse)
    def example_page(request: Request, name: str):
        job = _example(name)
        return render_job(request, storage.example_folder(name), job, f"/examples/{name}", example=name)

    @app.get("/examples/{name}/photo")
    def example_photo(name: str):
        job = _example(name)
        path = EXAMPLES / name / photos.markup_name(job["prefix"])
        if not path.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(path, media_type="image/jpeg")
