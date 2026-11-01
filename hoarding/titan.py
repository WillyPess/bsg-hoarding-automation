"""Titan uprights + counterweights from BSG's weight matrix (Internal Hoardings, Impact Certification Standards; Gus, 2026-11-01).
The matrix, the spare uprights and the external-job values live in rules.json."""
import math
from rules import RULES
# (maximum height m, upright centres m, counterweights per upright); none of these need bracing
MATRIX = [(r["max_height"], r["centres"], r["weights"]) for r in RULES["counterweights"]["matrix"]]
SPARE = RULES["uprights"]["spare"]   # 10% spare uprights, rounded up (Gus, 2026-11-01, v1.1)

def row(H):
    """The matrix row for a hoarding height: the first maximum height at or above it."""
    for r in MATRIX:
        if H <= r[0] + 1e-6: return r
    raise ValueError(f"{H} m is above the {MATRIX[-1][0]:g} m weight matrix")

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
    """(uprights to send, extra for wind, spare, weights per upright, weights to send).
    joins = uprights at the sheet joins, both run ends included. External jobs add the wind uprights first (rounded up),
    then the 10% spare goes on that total, rounded up: DJ Lift 24 -> 34 -> 38 (Gus, 2026-11-01).
    Weights = all uprights, spares included, x weights per upright; no separate spare weights (Gus, 2026-11-01): DJ Lift 38 x 8 = 304."""
    frac, wpu = wind(p)
    extra = math.ceil(round(joins * frac, 6))
    n = joins + extra
    spare = math.ceil(round(n * SPARE, 6))
    per = wpu or row(p["height"])[2]
    return n + spare, extra, spare, per, (n + spare) * per
