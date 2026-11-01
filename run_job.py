#!/usr/bin/env python3
"""Run the full BSG v1 pipeline for one job folder.

Usage (from the bundle root):
    python3 run_job.py hoarding/Bikini            # writes the outputs into hoarding/Bikini/
    python3 run_job.py hoarding/Bikini --out /tmp/x   # copies the job folder to /tmp/x first and writes there

Steps, same as CLAUDE.md "How to reproduce":
  0. job-specific scripts (Shrungaar/markup.py redraws the photo markup, Medibank/track_plan.py the track check plan)
  1. grid sheet (sheet.py / sheet_corner.py / sheet_u.py / sheet_firedoor.py, picked from job.json)
  2. melamine layout (layout_gen.py)
  3. materials form (materials.py) + PDF via LibreOffice
  4. package PDF (package_gen.py)
  5. Pacific Fair only: quotation (quotes/quote_gen.py, merged with quote_extras.json when present)
"dir" in job.json is replaced by the absolute job folder, so the job can live anywhere.
Prints a JSON summary of the key counts at the end (also saved as run_summary.json in the job folder).
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
H = os.path.join(ROOT, "hoarding")
PY = sys.executable
sys.path.insert(0, H)
from paths import soffice
ENV = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [H, os.environ.get("PYTHONPATH")]))}   # job scripts (markup.py, track_plan.py) import paths.py from any folder


def sh(args, cwd):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=ENV)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"FAILED: {' '.join(args)}")
    return r.stdout.strip()


def run(jobdir):
    jobdir = os.path.abspath(jobdir)
    job = json.load(open(os.path.join(jobdir, "job.json")))
    job["dir"] = jobdir
    P = job["prefix"]
    tmp = tempfile.mkdtemp()
    jp = os.path.join(tmp, "job.json"); json.dump(job, open(jp, "w"))
    js = json.dumps(job)
    log = {}
    # 0. job-specific scripts
    if os.path.exists(os.path.join(jobdir, "markup.py")) and any(f.startswith(P + "_photo") for f in os.listdir(jobdir)):
        sh([PY, "markup.py"], jobdir)
    if os.path.exists(os.path.join(jobdir, "track_plan.py")):  # draws from numbers, needs no photo
        sh([PY, "track_plan.py"], jobdir)
    # 1. grid sheet
    sheet_png = os.path.join(jobdir, f"{P}_hoarding_sheet.png")
    if "track" in job:
        sh([PY, f"{H}/sheet_firedoor.py", jp, sheet_png], jobdir)
    elif job.get("shape") == "U":
        sh([PY, f"{H}/sheet_u.py", jp, sheet_png], jobdir)
    elif "faces" in job:
        sh([PY, f"{H}/sheet_corner.py", jp, sheet_png], jobdir)
    else:
        # sheet.py works in mm and takes its own title (job.json is in metres)
        mm = {k: round(job[k] * 1000) for k in ("front", "return", "height", "door_offset", "door_width", "door_height")}
        mm["title"] = job.get("sheet_title", job["title"].upper() + ": HOARDING")
        sh([PY, f"{H}/sheet.py", json.dumps(mm), sheet_png], jobdir)
    # 2. melamine layout
    log["layout"] = json.loads(sh([PY, f"{H}/layout_gen.py", js, f"{jobdir}/{P}_melamine_layout.png"], jobdir).splitlines()[-1])
    # 3. materials
    log["materials"] = sh([PY, f"{H}/materials.py", f"{jobdir}/{P}_materials.xlsx", jp], jobdir).splitlines()[-1]
    sh([soffice(), "--headless", "--convert-to", "pdf", "--outdir", jobdir, f"{jobdir}/{P}_materials.xlsx"], jobdir)
    # 4. package
    log["package"] = sh([PY, f"{H}/package_gen.py", jp], jobdir).splitlines()[-1]
    # 5. quotation (Pacific Fair only)
    if job.get("site") == "Pacific Fair":
        q = dict(job)
        qe = os.path.join(jobdir, "quote_extras.json")
        if os.path.exists(qe):
            q.update(json.load(open(qe)))
        qp = os.path.join(tmp, "quote.json"); json.dump(q, open(qp, "w"))
        out = os.path.join(jobdir, job.get("quote_file", f"{P}_Quotation.pdf"))
        log["quote"] = sh([PY, f"{H}/quotes/quote_gen.py", qp, out], jobdir).splitlines()[-1]
    shutil.rmtree(tmp)
    summary = counts(job)
    summary["log"] = log
    json.dump(summary, open(os.path.join(jobdir, "run_summary.json"), "w"), indent=1)
    return summary


def counts(job):
    """Key numbers straight from the engine (same code paths as materials.py and quote_gen.py)."""
    sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "quotes"))
    from layout_gen import compute
    import titan
    from rules import RULES
    c = compute(job)
    joins = titan.joins(job, c)
    up, extra, spare, per, w = titan.for_job(job, joins)
    out = {"job": os.path.basename(job["dir"]), "run_m": c["L"], "height_m": job["height"],
           "layout_sheets": c["sheets"], "sheets_to_send": c["sheets"] + RULES["sheet"]["spare"], "tops": c["tops"],
           "uprights_at_joins": joins, "extra_uprights": extra, "spare_uprights": spare, "uprights_to_send": up,
           "weights_per_upright": per, "weights_to_send": w}
    if job.get("site") == "Pacific Fair":
        import quote_gen
        q = dict(job)
        qe = os.path.join(job["dir"], "quote_extras.json")
        if os.path.exists(qe):
            q.update(json.load(open(qe)))
        r = quote_gen.compute(q)
        out.update(quote_lm=r["charged"], quote_rate=r["rate"], quote_ex_gst=float(r["sub"]), quote_gst=float(r["gst"]),   # Decimal -> JSON number
                   quote_total=float(r["total"]), quote_poa_lines=sum(1 for l in r["lines"] if l[4] is None))
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    src = a[0]
    if "--out" in a:
        dst = os.path.abspath(a[a.index("--out") + 1])
        shutil.copytree(src, dst, dirs_exist_ok=True); src = dst
    print(json.dumps(run(src), indent=1))
