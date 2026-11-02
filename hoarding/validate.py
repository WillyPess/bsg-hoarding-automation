"""Input checks for a job.json, before the engine runs (PLAN-app.md §6).

check(job) -> list of Problem(field, message); an empty list means the job can run. run_job.py refuses a job with
problems, and the app shows them next to the form fields. The checks only use rules already in CLAUDE.md and
rules.json; nothing here computes a quantity. The job is never changed."""
import re
from dataclasses import dataclass

from rules import RULES
import titan

REQUIRED_TEXT = ("name", "prefix", "title", "site", "date")
REQUIRED_LENGTHS = ("front", "return", "height", "door_offset", "door_width")   # read by every script, also on faces jobs
PREFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")   # used in every output file name
CUTS = ("left", "right")
E = 1e-9   # length comparisons in metres (e.g. an entry that ends exactly at a corner)


@dataclass(frozen=True)
class Problem:
    field: str      # job.json key, e.g. "height", "faces[3].door_offset", "track.len"
    message: str

    def __str__(self):
        return f"{self.field}: {self.message}"


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _length(out, obj, key, field=None, allow_zero=False):
    """A positive number (or >= 0 with allow_zero). Returns the value, or None after adding a problem."""
    field = field or key
    if key not in obj:
        out.append(Problem(field, "is required"))
        return None
    v = obj[key]
    if not _number(v):
        out.append(Problem(field, f"must be a number in metres, not {v!r}"))
        return None
    if v < 0 or (v == 0 and not allow_zero):
        out.append(Problem(field, f"must be {'0 or more' if allow_zero else 'more than 0'}, not {v:g}"))
        return None
    return v


def _whole(out, obj, key, field=None):
    v = obj.get(key)
    if not (isinstance(v, int) and not isinstance(v, bool) and v > 0):
        out.append(Problem(field or key, f"must be a whole number more than 0, not {v!r}"))


def kind(job):
    """standard / corner / U / fire door, from the keys run_job.py uses to pick the grid sheet."""
    if "track" in job:
        return "fire door"
    if job.get("shape") == "U":
        return "U"
    if "faces" in job:
        return "corner"
    return "standard"


def check(job):
    out = []
    for key in REQUIRED_TEXT:
        v = job.get(key)
        if not isinstance(v, str) or not v.strip():
            out.append(Problem(key, "is required"))
    if isinstance(job.get("prefix"), str) and job["prefix"].strip() and not PREFIX.match(job["prefix"]):
        out.append(Problem("prefix", "may only use letters, digits, _ and - (it goes in every file name)"))

    L = {k: _length(out, job, k, allow_zero=(k == "door_offset")) for k in REQUIRED_LENGTHS}
    H = L["height"]
    top = titan.MATRIX[-1][0]
    if H is not None and H > top + E:
        out.append(Problem("height", f"{H:g} m is above the {top:g} m weight matrix: ask Gus which calculation to use (CLAUDE.md §6)"))
    dh = _length(out, job, "door_height") if "door_height" in job else RULES["defaults"]["door_height"]
    if H is not None and dh is not None and dh > H + E:
        out.append(Problem("door_height", f"the entry ({dh:g} m) can't be taller than the hoarding ({H:g} m)"))

    # 1.2 m kiosk (§4, Gus 2026-11-02): "kiosk": true only at exactly the kiosk height
    KH = RULES["kiosk"]["height"]
    if job.get("kiosk") and H is not None and abs(H - KH) > E:
        out.append(Problem("height", f"a kiosk (\"kiosk\": true) is {KH:g} m high, not {H:g} m: ask Gus how to build and price this one"))
    # external jobs (§7)
    if job.get("external"):
        if H is not None and abs(H - 2.4) > E:
            out.append(Problem("height", f"external jobs are always 2.4 m high (CLAUDE.md §7), not {H:g} m"))
        if "extra_weight_pct" not in job:
            out.append(Problem("extra_weight_pct", f'{titan.QUESTION} Put the answer in "extra_weight_pct" (0 = no extra weight).'))
        elif not _number(job["extra_weight_pct"]) or job["extra_weight_pct"] < 0:
            out.append(Problem("extra_weight_pct", f"must be a number, 0 or more (the % the user gave), not {job['extra_weight_pct']!r}"))
    elif "extra_weight_pct" in job:
        out.append(Problem("extra_weight_pct", "is only for external jobs"))

    if "uprights" in job:
        _whole(out, job, "uprights")

    k = kind(job)
    dw = L["door_width"]
    if k == "standard":
        if None not in (L["door_offset"], dw, L["front"]) and L["door_offset"] + dw > L["front"] + E:
            out.append(Problem("door_offset", f"the entry ({L['door_offset']:g} + {dw:g} m) runs past the end of the {L['front']:g} m front"))
    else:
        out += _faces(job, k, dw)
    if k == "fire door":
        out += _track(job)
    return out


def _faces(job, k, dw):
    out = []
    faces = job.get("faces")
    if not isinstance(faces, list) or not faces:
        return [Problem("faces", "is required (a list of faces, left to right as seen from the mall)")]
    if k == "U" and len(faces) != 5:
        out.append(Problem("faces", f"a U job has 5 faces (left return, left side, front, right side, right return), not {len(faces)}"))
    entries = []
    for i, f in enumerate(faces):
        if not isinstance(f, dict):
            out.append(Problem(f"faces[{i}]", "must be a face (name, len, cut or door_offset)"))
            continue
        if not isinstance(f.get("name"), str) or not f["name"].strip():
            out.append(Problem(f"faces[{i}].name", "is required"))
        n = _length(out, f, "len", f"faces[{i}].len")
        if "cut" in f and f["cut"] not in CUTS:
            out.append(Problem(f"faces[{i}].cut", f'must be "left" or "right", not {f["cut"]!r}'))
        if "door_offset" in f:
            entries.append(i)
            o = _length(out, f, "door_offset", f"faces[{i}].door_offset", allow_zero=True)
            if None not in (o, n, dw) and o + dw > n + E:
                out.append(Problem(f"faces[{i}].door_offset", f"the entry ({o:g} + {dw:g} m) runs past the end of the {n:g} m {f.get('name', 'face')}"))
    if len(entries) != 1:
        out.append(Problem("faces", f"exactly one face must have the entry (door_offset), not {len(entries)}"))
    return out


def _track(job):
    out = []
    t = job.get("track")
    if not isinstance(t, dict):
        return [Problem("track", "must give face, len, studs and lengths")]
    names = {f.get("name"): f for f in job.get("faces", []) if isinstance(f, dict)}
    if t.get("face") not in names:
        out.append(Problem("track.face", f"must be the name of one of the faces, not {t.get('face')!r}"))
    n = _length(out, t, "len", "track.len")
    face_len = names.get(t.get("face"), {}).get("len")
    if n is not None and _number(face_len) and n > face_len + E:
        out.append(Problem("track.len", f"the track section ({n:g} m) is longer than the {face_len:g} m {t['face']}"))
    _whole(out, t, "studs", "track.studs")
    _whole(out, t, "lengths", "track.lengths")
    for key in ("shopfront", "step", "push"):
        _length(out, job, key, allow_zero=(key == "push"))
    return out
