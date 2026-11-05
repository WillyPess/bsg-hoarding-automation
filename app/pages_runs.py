"""Run and results pages (PLAN-app.md, Demo scope, PR A): the Run button, the "running..." state, the results page and
its downloads, for jobs (/jobs/<folder>/...) and Examples (/examples/<name>/..., on their copy in the data folder).

The page shows what the run folder holds: every number comes from the run's run_summary.json, as it is, and the
warnings from the engine, on the run's own job.json and summary."""
import json

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app import engine, pages_jobs, runner, storage


def _value(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


def _metres(v):
    return f"{_value(v)} m"


def _lm(v):
    return f"{_value(v)} lm"


def _percent(v):
    return f"{_value(v)}%"


def _money(v):
    return f"${v:,.2f}"


# (label, run_summary.json key, format)
MATERIALS = [("Run", "run_m", _metres), ("Height", "height_m", _metres),
             ("Melamine sheets in the layout", "layout_sheets", _value), ("Melamine sheets to send, with spares", "sheets_to_send", _value),
             ("Stock sheet height", "sheet_h", _metres), ("Cut-offs to tops stock", "cut_offs_to_tops_stock", _value),
             ("Tops to cut from offcuts", "tops", _value), ("Top sizes", "tops_from_offcuts", _value),
             ("Uprights at the joins", "uprights_at_joins", _value), ("Extra uprights for wind", "extra_uprights", _value),
             ("Spare uprights", "spare_uprights", _value), ("Uprights to send", "uprights_to_send", _value),
             ("Anti-tampers to send", "anti_tampers_to_send", _value), ("Counterweights per upright", "weights_per_upright", _value),
             ("Counterweights for the uprights", "weights_to_send", _value), ("Extra weight asked", "extra_weight_pct", _percent),
             ("Extra counterweights", "extra_weights", _value), ("Counterweights to send", "total_weights_to_send", _value),
             ("White tape rolls", "white_tape_rolls", _value), ("Black tape rolls", "black_tape_rolls", _value)]
QUOTE = [("Length charged", "quote_lm", _lm), ("Rate per lm", "quote_rate", _money), ("Total ex GST", "quote_ex_gst", _money),
         ("GST", "quote_gst", _money), ("Total inc GST", "quote_total", _money)]
HIDDEN_AT_ZERO = {"extra_uprights"}    # nothing to say on most jobs
TOTALS = {"sheets_to_send", "uprights_to_send", "total_weights_to_send", "quote_total"}


def _rows(table, summary):
    out = []
    for label, key, fmt in table:
        v = summary.get(key)
        if v in (None, "") or (key in HIDDEN_AT_ZERO and not v):
            continue
        out.append({"key": key, "label": label, "value": fmt(v), "total": key in TOTALS})
    return out


def _quote_rows(summary):
    """The quote's rows, then one row per POA line, by the engine's own name (quote_poa_names). A run made before
    the names were in run_summary.json shows the count it has."""
    rows = _rows(QUOTE, summary)
    if not rows:
        return rows
    names = summary.get("quote_poa_names")
    if names is None and summary.get("quote_poa_lines"):
        return rows + [{"key": "quote_poa_lines", "label": "Lines at POA, not in the total", "value": _value(summary["quote_poa_lines"]), "total": False}]
    return rows + [{"key": "quote_poa", "label": n, "value": "POA", "total": False} for n in names or []]


def _drawings(job):
    P = job["prefix"]
    return [("Grid sheet", f"{P}_hoarding_sheet.png"), ("Melamine layout", f"{P}_melamine_layout.png")]


def _downloads(job):
    P = job["prefix"]
    return [("Package PDF", f"{P}_Hoarding_Package.pdf"), ("Materials PDF", f"{P}_materials.pdf"), ("Materials XLSX", f"{P}_materials.xlsx"),
            ("Quote PDF", job.get("quote_file", f"{P}_Quotation.pdf"))]


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


NO_PHOTO = "Upload the marked-up photo to run."   # the package needs it on its first page


def add_routes(app, page, settings):
    def run_page(request, folder, number, base, title_link, can_run=True):
        row = storage.get_run(settings, folder, number)
        if row is None:
            raise HTTPException(status_code=404)
        path = storage.run_dir(settings, folder, number)
        job = _read_json(path / "job.json")
        ctx = {"can_run": can_run, "job": job, "folder": folder, "base": base, "run_url": f"{base}/runs/{number}", "title_link": title_link, "number": number,
               "row": row, "when": pages_jobs._when(row["finished_at"] or row["started_at"]), "seconds": _read_json(path / "engine.json").get("seconds")}
        if row["status"] == "running":
            ctx["elapsed"] = max(0, int(storage.now() - row["started_at"]))
        elif row["status"] == "done":
            summary = _read_json(path / "run_summary.json")
            ctx.update(materials=_rows(MATERIALS, summary), quote=_quote_rows(summary), warnings=engine.warnings(job, summary),
                       drawings=[(label, name) for label, name in _drawings(job) if (path / name).is_file()],
                       downloads=[(label, name) for label, name in _downloads(job) if (path / name).is_file()])
        return page(request, "run.html", tab="jobs", **ctx)

    def send_file(request, folder, number, name):
        row = storage.get_run(settings, folder, number)
        if row is None or row["status"] != "done":
            raise HTTPException(status_code=404)
        path = storage.run_dir(settings, folder, number)
        job = _read_json(path / "job.json")
        try:
            storage._check_file_name(name)
        except storage.StorageError:
            raise HTTPException(status_code=404) from None
        if not (path / name).is_file():
            raise HTTPException(status_code=404)
        if name in [n for _, n in _drawings(job)]:
            return FileResponse(path / name, media_type="image/png")     # shown on the page
        if name in [n for _, n in _downloads(job)]:
            storage.record(settings, request.state.user.id, "file.downloaded", folder, number, file=name)   # downloads are recorded
            return FileResponse(path / name, filename=name)              # saved by the browser
        raise HTTPException(status_code=404)                             # only the results: not job.json, engine.json, ...

    @app.post("/jobs/{folder}/run")
    def run_a_job(request: Request, folder: str):
        pages_jobs._job_or_404(settings, folder)
        if not storage.has_photo(settings, folder):        # the button is disabled; this is for a stale page or a script
            raise HTTPException(status_code=409, detail=NO_PHOTO)
        runner.start(settings, folder, request.state.user.id)
        return RedirectResponse(f"/jobs/{folder}", status_code=303)       # the job page says "Generating PDFs" until it is done

    @app.get("/jobs/{folder}/runs/{number}", response_class=HTMLResponse)
    def job_run_page(request: Request, folder: str, number: int):
        pages_jobs._job_or_404(settings, folder)
        return run_page(request, folder, number, f"/jobs/{folder}", f"/jobs/{folder}", can_run=storage.has_photo(settings, folder))

    @app.get("/jobs/{folder}/runs/{number}/files/{name}")
    def job_run_file(request: Request, folder: str, number: int, name: str):
        pages_jobs._job_or_404(settings, folder)
        return send_file(request, folder, number, name)

    @app.post("/examples/{name}/run")
    def run_an_example(request: Request, name: str):
        source = pages_jobs.example_dir(name)
        user = request.state.user
        runner.start(settings, storage.example_folder(name), user.id,
                     prepare=lambda: storage.copy_example(settings, name, source, user.id))
        return RedirectResponse(f"/examples/{name}", status_code=303)

    @app.get("/examples/{name}/runs/{number}", response_class=HTMLResponse)
    def example_run_page(request: Request, name: str, number: int):
        pages_jobs.example_dir(name)
        return run_page(request, storage.example_folder(name), number, f"/examples/{name}", f"/examples/{name}")

    @app.get("/examples/{name}/runs/{number}/files/{file}")
    def example_run_file(request: Request, name: str, number: int, file: str):
        pages_jobs.example_dir(name)
        return send_file(request, storage.example_folder(name), number, file)
