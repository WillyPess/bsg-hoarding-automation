"""Form inputs -> job.json, and the warnings a reviewer must see (PLAN-app.md §6, step 2).

normalize(inputs) is the only place that turns the new-job form's inputs into job.json:
  - the entry position as Gus gives it, from either end ("entry_from": "left"/"right", "entry_offset" in metres),
    becomes door_offset from the left end of the front (or of the entry face on corner / U / fire-door jobs);
  - defaults (return, entry width and height) come from rules.json;
  - faces jobs get the top-level keys every script reads (front, return, door_offset; right_return when it differs).
  - extra_weight_pct is never filled in (§7): an external job without it stays without it, and validate asks.
Lengths are converted in whole mm, so 20.0 - 6.0 - 1.6 gives 12.4, not 12.399999999999999.

warnings(job, summary) lists what the reviewer must know before approving, each JobWarning(rule, message) naming the
rules.json entry (provisional) or the CLAUDE.md section it comes from. It never changes a number."""
import os, re
from dataclasses import dataclass

from rules import RULES

KINDS = ("standard", "corner", "U", "fire door")
ENDS = ("left", "right")
PASS = {   # job.json keys copied as given (see CLAUDE.md, "job.json")
    "name", "prefix", "title", "site", "date", "by", "height", "front", "return", "door_width", "door_height", "sheet_h",
    "entry_note", "photo_note", "photo_text", "photo_h", "front_ends", "sheet_title", "estimated",
    "external", "extra_weight_pct", "extra_uprights", "weights_per_upright", "uprights",
    "track", "shopfront", "step", "push", "no_corner_uprights",
    "quote_no", "quote_date", "quote_file", "valid_days", "kiosk", "extra_doors", "extra_doors_after", "passage_sets",
    "scope", "extra_lines", "price_notes", "terms_notes"}
FACE_KEYS = {"name", "len", "cut", "entry_from", "entry_offset"}


def _mm(x):
    return int(round(x * 1000))


def _offset_from_left(length, width, end, offset):
    """door_offset from the left end, given the entry's distance from the end Gus measured from."""
    if end not in ENDS:
        raise ValueError(f'entry_from must be "left" or "right", not {end!r}')
    if end == "left":
        return offset
    return (_mm(length) - _mm(offset) - _mm(width)) / 1000


def suggest_prefix(title):
    """A file-name-safe prefix from the job title: "David Jones - Lift Area" -> "DavidJonesLiftArea"."""
    words = re.findall(r"[A-Za-z0-9]+", title)
    return "".join(w if w.isupper() else w[:1].upper() + w[1:] for w in words)


def normalize(inputs, jobs_dir=None):
    """New-job form inputs -> job.json (a new dict; inputs are not changed). jobs_dir sets "dir" = jobs_dir/prefix."""
    kind = inputs.get("kind")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}, not {kind!r}")
    unknown = set(inputs) - PASS - {"kind", "entry_from", "entry_offset", "faces"}
    if unknown:
        raise ValueError(f"unknown input(s): {', '.join(sorted(unknown))}")
    D = RULES["defaults"]
    job = {k: v for k, v in inputs.items() if k in PASS}
    job.setdefault("name", inputs.get("title"))
    job.setdefault("door_width", D["door_width"])
    job.setdefault("door_height", D["door_height"])
    if kind == "standard":
        job.setdefault("return", D["return"])
        job["door_offset"] = _offset_from_left(job["front"], job["door_width"], inputs.get("entry_from"), inputs.get("entry_offset"))
    else:
        faces, entry = [], None
        for i, f in enumerate(inputs.get("faces") or []):
            bad = set(f) - FACE_KEYS
            if bad:
                raise ValueError(f"faces[{i}]: unknown key(s) {', '.join(sorted(bad))}")
            face = {k: v for k, v in f.items() if k in ("name", "len", "cut")}
            if "entry_from" in f or "entry_offset" in f:
                if entry is not None:
                    raise ValueError("only one face can have the entry")
                entry = face
                face["door_offset"] = _offset_from_left(f["len"], job["door_width"], f.get("entry_from"), f.get("entry_offset"))
            faces.append(face)
        if entry is None:
            raise ValueError("one face must have the entry (entry_from and entry_offset)")
        front = [f for f in faces if f.get("name") == "front"]
        if len(front) != 1:
            raise ValueError('a faces job needs exactly one face named "front"')
        job["faces"] = faces
        job["front"] = front[0]["len"]
        job["return"] = faces[0]["len"]
        if faces[-1]["len"] != faces[0]["len"]:
            job["right_return"] = faces[-1]["len"]
        job["door_offset"] = entry["door_offset"]
        if kind == "corner":
            job["corner"] = True
        elif kind == "U":
            job["shape"] = "U"
    if jobs_dir is not None:
        job["dir"] = os.path.join(jobs_dir, job["prefix"])
    return job


# --- warnings ---------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class JobWarning:
    rule: str       # a provisional rules.json entry ("tape.spare") or a CLAUDE.md section ("CLAUDE.md §10")
    message: str

    def __str__(self):
        return f"{self.message} ({self.rule})"


def _kind(job):
    if "track" in job:
        return "fire door"
    if job.get("shape") == "U":
        return "U"
    return "corner" if "faces" in job else "standard"


def warnings(job, summary):
    """What the reviewer must know before approving this run. job = job.json, summary = run_summary.json."""
    R, M = RULES, RULES["materials"]
    out = []
    w = lambda rule, msg: out.append(JobWarning(rule, msg))
    # provisional rules every job uses
    w("materials.studs", f"Studs: {M['studs']} per {M['per_length']:g} m of run, inferred from Just Cuts, not formally confirmed.")
    ds = R["door_set"]
    w("door_set.studs_short_length", f"Door studs: {ds['studs_short']} x {ds['studs_short_length']:g} m, purpose still unknown (Gus is asking his boss).")
    if R["tape"]["tape_rule"] == "joints":
        w("tape.spare", f"White tape: joint length + {R['tape']['spare']:.0%} spare; the spare is provisional until Gus's boss confirms it.")
    else:
        w("materials.white_tape", f"White tape: v1 rule, {M['white_tape']} rolls per {M['per_length']:g} m (tape.tape_rule = \"v1\").")
    b = R["black_tape"]
    w("black_tape.spare", f"Black tape: full run x {1 + b['spare']:g} / {b['roll_length']:g} m rolls, provisional (Gus, 2026-11-02).")
    # job features
    if job.get("external"):
        e = R["external"]
        w("external.extra_uprights", f"External job: {job.get('extra_uprights', e['extra_uprights']):.0%} extra uprights for wind, provisional (no official table yet).")
        w("external.weights_per_upright", f"External job: {job.get('weights_per_upright') or e['weights_per_upright']} counterweights per upright, provisional (no official table yet).")
    kind = _kind(job)
    if kind == "corner":
        w("CLAUDE.md §8", "Outside corner = a normal joint with one upright, provisional until Gus's boss confirms.")
    if kind == "fire door":
        w("CLAUDE.md §10", "Track + timbers is a suggestion only; BSG is still learning this method.")
    if "uprights" in job:
        w("CLAUDE.md §5", f"Uprights at the joins set by hand ({job['uprights']}), not from the layout; the 10% spare is added on top.")
    if job.get("entry_note"):
        w("CLAUDE.md §1", f"Entry: {job['entry_note'].lstrip(', ').rstrip('.')}. Check it still lines up with the shop entrance.")
    if job.get("estimated"):
        w("CLAUDE.md §1", f"Sizes read from the photo are estimates ({', '.join(job['estimated'])}): ask Gus for the site measurements.")
    if summary.get("tops"):
        w("CLAUDE.md §3", f"{summary['tops']} tops to cut from offcuts ({summary.get('tops_from_offcuts', '')}): the loader adds a sheet for each size not in stock.")
    if job.get("site") == "Pacific Fair":
        w("rate_card.bands", f"Quote from \"{R['rate_card']['name']}\": its printed validity has ended; Gus keeps using it until a new card comes.")
        if summary.get("quote_poa_lines"):
            w("CLAUDE.md §12", f"The quote has {summary['quote_poa_lines']} POA line(s) (price on application), not in the total.")
    return out
