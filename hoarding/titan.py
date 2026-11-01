"""Titan uprights + counterweights from BSG's weight matrix (Internal Hoardings, Impact Certification Standards; Gus, 2026-11-01).
The matrix, the spare and the external-job values live in rules.json."""
import math
from rules import RULES
# (maximum height m, upright centres m, counterweights per upright); none of these need bracing
MATRIX = [(r["max_height"], r["centres"], r["weights"]) for r in RULES["counterweights"]["matrix"]]
EXTRA = RULES["counterweights"]["spare"]   # always send 10% more weights as spare (Gus, 2026-11-01)

def row(H):
    """The matrix row for a hoarding height: the first maximum height at or above it."""
    for r in MATRIX:
        if H <= r[0] + 1e-6: return r
    raise ValueError(f"{H} m is above the {MATRIX[-1][0]:g} m weight matrix")

def counterweights(uprights, H):
    """(per upright, total to send incl. 10% spare, rounded up)."""
    per = row(H)[2]
    return per, math.ceil(round(uprights * per * (1 + EXTRA), 6))

def joins(p, c):
    """Uprights at the sheet joins: one per upright position in the layout (c = layout_gen.compute(p)),
    or "uprights" in job.json when set by hand (corners that can't take uprights, fire-door jobs, Gus 2026-10-28)."""
    return p.get("uprights", len(c["uprights"]))

def wind(p):
    """(extra uprights as a fraction, weights per upright or None) for an external job ("external": true), from rules.json
    (Gus 2026-11-01, David Jones Lift Area). "extra_uprights" / "weights_per_upright" in job.json override them for one job."""
    ext = RULES["external"] if p.get("external") else {"extra_uprights": 0, "weights_per_upright": None}
    return p.get("extra_uprights", ext["extra_uprights"]), p.get("weights_per_upright") or ext["weights_per_upright"]

def for_job(p, joins):
    """(uprights to send, how many of them are extra, weights per upright, weights to send incl. 10% spare).
    joins = uprights at the sheet joins. External jobs add uprights and replace the matrix value (wind)."""
    frac, wpu = wind(p)
    extra = math.ceil(round(joins * frac, 6))
    n = joins + extra
    per = wpu or row(p["height"])[2]
    return n, extra, per, math.ceil(round(n * per * (1 + EXTRA), 6))
