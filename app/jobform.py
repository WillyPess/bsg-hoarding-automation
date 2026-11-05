"""The new/edit job form for standard jobs (+ the kiosk tick box), PLAN-app.md §6; §11 step 4.

read() turns the posted form into the inputs jobs.normalize takes, and process() runs normalize and validate.check
and puts each problem next to its form field. The form only parses what was typed (text to numbers); every default,
conversion (entry from the right end) and check is the engine's. Fields this form doesn't have (external, faces,
extra weight, ...) are never read from a post: those job types are built in later steps."""
import time

from app import engine

SITES = ("Pacific Fair", "Hyperdome")   # the known sites (CLAUDE.md §12); anything else is "Other"
LENGTHS = ("front", "return", "height", "door_width", "door_height", "entry_offset")
LABELS = {"title": "Job title", "site": "Site", "date": "Date", "prefix": "Prefix", "front": "Front width",
          "return": "Returns (each side)", "height": "Height", "door_width": "Entry width", "door_height": "Entry height",
          "entry_from": "Measured from", "entry_offset": "Entry position", "entry_note": "Entry note",
          "kiosk": "Kiosk", "client": "Client", "drawings_sent_by": "Drawings sent by", "extra_doors": "Extra door sets",
          "passage_sets": "Passage sets", "photo_note": "Notes for the job sheet", "dust_suppression": "Dust suppression",
          "ladder": "Ladder", "photo": "Marked-up photo", "note": "What was wrong"}
CLIENT = "GPT - Pacific Fair"           # the form's default client (Pacific Fair quotes are addressed to GPT, §12)
COUNTS = ("extra_doors", "passage_sets")
TICKS = ("dust_suppression", "ladder")  # markers only: job.json + a line on the materials form, no calculation
# job.json keys the form manages; on an edit, every other key in job.json is kept as it was
FORM_KEYS = {"title", "name", "site", "date", "prefix", "front", "return", "height", "door_width", "door_height",
             "door_offset", "entry_note", "kiosk", "estimated", "client", "drawings_sent_by", "extra_doors", "passage_sets",
             "photo_note", "dust_suppression", "ladder"}
TO_FIELD = {"door_offset": "entry_offset", "name": "title"}       # validate's job.json field -> the form field
TO_JOB = {"entry_offset": "door_offset"}                          # estimate ticks: form field -> job.json field


def fmt(x):
    return "" if x is None else f"{x:g}" if isinstance(x, (int, float)) and not isinstance(x, bool) else str(x)


def blank(user):
    """Values for an empty new-job form: nothing pre-selected, today's date, prepared by the logged-in user."""
    return {"title": "", "site": "", "site_other": "", "date": time.strftime("%d/%m/%Y"), "prefix": "", "entry_from": "",
            "kiosk": False, "estimates": set(), "by": user.name, **{f: "" for f in LENGTHS}, "entry_note": "",
            "client": CLIENT, "drawings_sent_by": "", "extra_doors": "0", "passage_sets": "0", "photo_note": "",
            "dust_suppression": False, "ladder": False}


def from_job(job):
    """Form values from an existing job.json (the entry is shown from the left end, as job.json keeps it)."""
    site = job.get("site", "")
    v = {"title": job.get("title", ""), "site": site if site in SITES else ("other" if site else ""),
         "site_other": "" if site in SITES else site, "date": job.get("date", ""), "prefix": job.get("prefix", ""),
         "entry_from": "left", "kiosk": bool(job.get("kiosk")), "entry_note": job.get("entry_note", ""),
         "by": job.get("by", ""), "client": job.get("client", ""), "drawings_sent_by": job.get("drawings_sent_by", ""),
         "extra_doors": fmt(job.get("extra_doors", 0)), "passage_sets": fmt(job.get("passage_sets", 0)),
         "photo_note": job.get("photo_note", ""), **{t: job.get(t) is True for t in TICKS}}
    for f in LENGTHS:
        v[f] = fmt(job.get(TO_JOB.get(f, f)))
    est = set(job.get("estimated", []))
    v["estimates"] = {f for f in LENGTHS if TO_JOB.get(f, f) in est}
    return v


def _number(text):
    return float(text.strip().replace(",", "."))


def read(form, user, prefix=None, by=None):
    """(values to show again, inputs for normalize, {field: message} for what couldn't be read)."""
    g = lambda k: str(form.get(k) or "").strip()
    v = {"title": g("title"), "site": g("site"), "site_other": g("site_other"), "date": g("date"),
         "prefix": prefix if prefix is not None else g("prefix"), "entry_from": g("entry_from"),
         "kiosk": form.get("kiosk") is not None, "entry_note": str(form.get("entry_note") or ""),
         "estimates": {f for f in LENGTHS if form.get(f"estimate_{f}") is not None}, "by": by or user.name,
         **{f: g(f) for f in LENGTHS}, "client": g("client"), "drawings_sent_by": g("drawings_sent_by"),
         **{c: g(c) for c in COUNTS}, "photo_note": str(form.get("photo_note") or "").strip(),
         **{t: form.get(t) is not None for t in TICKS}}
    problems = {}
    inputs = {"kind": "standard", "title": v["title"], "date": v["date"], "by": v["by"]}
    if v["site"] == "other":
        site = v["site_other"]
    elif v["site"] in SITES:
        site = v["site"]
    else:
        site = ""
    if not site:
        problems["site"] = "choose the site (Pacific Fair jobs get a quote)" if v["site"] != "other" else "choose the site: type its name"
    inputs["site"] = site
    inputs["prefix"] = v["prefix"] or (engine.suggest_prefix(v["title"]) if v["title"] else "")
    v["prefix_used"] = inputs["prefix"]
    for f in ("front", "return", "height", "door_width", "door_height"):
        if v[f]:
            try:
                inputs[f] = _number(v[f])
            except ValueError:
                problems[f] = f"must be a number in metres (e.g. 4.5), not {v[f]!r}"
    if v["entry_from"] in ("left", "right"):
        inputs["entry_from"] = v["entry_from"]
    else:
        problems["entry_from"] = "choose whether the entry is measured from the left or the right end of the front"
    if v["entry_offset"]:
        try:
            inputs["entry_offset"] = _number(v["entry_offset"])
        except ValueError:
            problems["entry_offset"] = f"must be a number in metres (e.g. 1.2), not {v['entry_offset']!r}"
    else:
        problems["entry_offset"] = "is required: how far the entry starts from that end, in metres"
    if v["entry_note"].strip():
        inputs["entry_note"] = v["entry_note"]
    if v["kiosk"]:
        inputs["kiosk"] = True
    for k in ("client", "drawings_sent_by", "photo_note"):
        if v[k]:
            inputs[k] = v[k]
    for c in COUNTS:
        text = v[c] or "0"
        if text.isdigit():
            if int(text):
                inputs[c] = int(text)
        else:
            problems[c] = f"must be a whole number, 0 or more, not {v[c]!r}"
    for t in TICKS:
        if v[t]:
            inputs[t] = True
    if v["estimates"]:
        inputs["estimated"] = [TO_JOB.get(f, f) for f in LENGTHS if f in v["estimates"]]
    return v, inputs, problems


def process(form, user, prefix=None, by=None, keep=None):
    """(values, job.json or None, {field: [messages]}). job is None when there is any problem: nothing may be written.
    keep: the existing job.json on an edit; its keys the form doesn't manage are kept as they were."""
    v, inputs, parse = read(form, user, prefix, by)
    problems = {f: [m] for f, m in parse.items()}
    # A trial pass so every other field still gets checked when one can't be read: stand-in values for the entry
    # and the front, used only here and never written (there is a problem, so job stays None).
    trial = dict(inputs)
    stand_ins = set()
    if "front" not in trial:
        if "front" not in problems:
            problems["front"] = ["is required"]
        trial["front"] = 1.0
        stand_ins.add("front")
    if "entry_from" not in trial or "entry_offset" not in trial or "front" in stand_ins:
        trial.update(entry_from="left", entry_offset=0.0)
        stand_ins.add("entry_offset")   # the entry can't be checked without a real front and a real entry
    try:
        job = engine.normalize(trial)
    except (ValueError, TypeError) as e:
        problems.setdefault("form", []).append(str(e))
        return v, None, problems
    if keep:
        for k, val in keep.items():
            if k not in FORM_KEYS and k not in job:
                job[k] = val
    for p in engine.check(job):
        field = TO_FIELD.get(p.field, p.field)
        if field in parse or field in stand_ins:   # already said more precisely, or about a stand-in value: say nothing
            continue
        msgs = problems.setdefault(field if field in LABELS else "form", [])
        msg = p.message if field in LABELS else str(p)
        if msg not in msgs:
            msgs.append(msg)
    return v, (None if problems else job), problems
