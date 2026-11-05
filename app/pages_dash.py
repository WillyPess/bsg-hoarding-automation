"""Dashboard and Activity (engenai UI).

Dashboard: every job and Example with PDFs, by its latest finished run. Each total is a sum of those runs'
run_summary.json values (the engine's numbers, as they are); nothing is worked out again. Corrections are the
Fix job entries of the audit. Activity: the audit, latest first."""
import time
from decimal import Decimal

from fastapi import Request
from fastapi.responses import HTMLResponse

from app import pages_jobs, storage, views

COLOURS = ("#4a90d9", "#9cc3ef", "#2f6bb0", "#6fb1f0", "#c7dcf5")   # one per site, in the order the sites come
MATERIALS = [("Sheets", "sheets_to_send"), ("Tops", "tops"), ("Uprights", "uprights_to_send"), ("Weights", "total_weights_to_send")]


def total(rows, key):
    return sum((Decimal(str(r["summary"][key])) for r in rows if isinstance(r["summary"].get(key), (int, float))), Decimal(0))


def plain(d):
    return f"{d.normalize():f}" if d != d.to_integral_value() else f"{int(d)}"


def chart(rows):
    """Lineal metres per month by site, as SVG bars: {months, sites, bars, ticks, width, height}."""
    months, lm = [], {}
    for r in sorted(rows, key=lambda r: r["finished_at"]):
        m = time.strftime("%b %Y", time.localtime(r["finished_at"]))
        site = r["site"] or "Other"
        if m not in months:
            months.append(m)
        lm[(m, site)] = lm.get((m, site), Decimal(0)) + Decimal(str(r["summary"].get("run_m", 0)))
    by_site = {}
    for (m, site), v in lm.items():
        by_site[site] = by_site.get(site, Decimal(0)) + v
    sites = sorted(by_site, key=lambda s: (-by_site[s], s))      # the biggest site first, in the darkest blue
    top = max(lm.values(), default=Decimal(0))
    step = next((s for s in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if top / s <= 5), 2000)
    ymax = max(step * 4, ((int(top) // step) + 1) * step)
    W, H, left, bottom, topm = 620, 300, 52, 40, 14
    plot_h = H - bottom - topm
    group = (W - left - 20) / max(len(months), 1)
    bw = min(56, group / (len(sites) + 1))
    bars = []
    for i, m in enumerate(months):
        x0 = left + i * group + (group - bw * len(sites) - 6 * (len(sites) - 1)) / 2
        for j, site in enumerate(sites):
            v = lm.get((m, site))
            if v:
                h = float(v) / ymax * plot_h
                bars.append({"x": round(x0 + j * (bw + 6), 1), "y": round(H - bottom - h, 1), "w": round(bw, 1), "h": round(h, 1),
                             "fill": COLOURS[j % len(COLOURS)], "title": f"{site}, {m}: {plain(v)} lm"})
    ticks = [{"y": round(H - bottom - t / ymax * plot_h, 1), "label": t} for t in range(0, ymax + 1, step)]
    labels = [{"x": round(left + (i + .5) * group, 1), "label": m} for i, m in enumerate(months)]
    return {"bars": bars, "ticks": ticks, "labels": labels, "sites": [(s, COLOURS[j % len(COLOURS)]) for j, s in enumerate(sites)],
            "width": W, "height": H, "left": left, "right": W - 20, "base": H - bottom}


def add_routes(app, page, settings):
    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard(request: Request):
        rows = [r for r in pages_jobs.all_entries(settings) if r["summary"] and r["finished_at"]]
        people = {}
        for r in rows:
            who = r["created_by"] or "—"
            people[who] = people.get(who, 0) + 1
        most = max(people.values(), default=1)
        corrections = []
        for a in storage.activity(settings, limit=5, actions=["job.corrected"]):
            corrections.append({"when": views.when(a["at"]), "user": a["user"], "title": a["title"] or a["job"], "url": views.job_url(a["job"]),
                                "note": a["detail"].get("note", "")})
        return page(request, "dashboard.html", tab="dashboard", n=len(rows), lm=plain(total(rows, "run_m")),
                    quoted=views.money(total(rows, "quote_ex_gst")), n_corrections=storage.count_actions(settings, "job.corrected"),
                    chart=chart(rows), people=sorted(people.items(), key=lambda p: (-p[1], p[0])), most=most,
                    corrections=corrections, materials=[(label, plain(total(rows, key))) for label, key in MATERIALS])

    @app.get("/activity", response_class=HTMLResponse)
    def activity(request: Request):
        rows = []
        for a in storage.activity(settings, limit=300):
            if a["action"] in views.HIDDEN:
                continue
            text, note = views.describe(a)
            rows.append({"when": views.when(a["at"]), "user": a["user"], "text": text, "note": note,
                         "job": (a["title"] or a["job"]) if a["job"] else "", "url": views.job_url(a["job"]) if a["job"] else ""})
        return page(request, "activity.html", tab="activity", rows=rows)
