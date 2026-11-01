"""Titan uprights + counterweights from BSG's weight matrix (Internal Hoardings, Impact Certification Standards; Gus, 2026-11-01)."""
import math
# (maximum height m, upright centres m, counterweights per upright); none of these need bracing
MATRIX = [(1.2, 2.4, 2), (1.8, 1.2, 3), (2.4, 1.2, 4), (3.0, 1.2, 4), (3.6, 1.2, 5), (4.2, 1.2, 6),
          (4.8, 1.2, 7), (5.4, 1.2, 8), (6.0, 1.2, 9), (6.6, 1.2, 11), (7.2, 1.2, 12)]
EXTRA = 0.10   # always send 10% more weights as spare (Gus, 2026-11-01)

def row(H):
    """The matrix row for a hoarding height: the first maximum height at or above it."""
    for r in MATRIX:
        if H <= r[0] + 1e-6: return r
    raise ValueError(f"{H} m is above the 7.2 m weight matrix")

def counterweights(uprights, H):
    """(per upright, total to send incl. 10% spare, rounded up)."""
    per = row(H)[2]
    return per, math.ceil(round(uprights * per * (1 + EXTRA), 6))

def joins(p, c):
    """Uprights at the sheet joins: one per upright position in the layout (c = layout_gen.compute(p)),
    or "uprights" in job.json when set by hand (corners that can't take uprights, fire-door jobs, Gus 2026-10-28)."""
    return p.get("uprights", len(c["uprights"]))

def for_job(p, joins):
    """(uprights to send, how many of them are extra, weights per upright, weights to send incl. 10% spare).
    joins = uprights at the sheet joins. A job can ask for more (external jobs, Gus 2026-11-01, David Jones Lift Area):
    "extra_uprights": 0.4 adds 40% more uprights (rounded up), "weights_per_upright": 8 replaces the matrix value."""
    extra = math.ceil(round(joins * p.get("extra_uprights", 0), 6))
    n = joins + extra
    per = p.get("weights_per_upright") or row(p["height"])[2]
    return n, extra, per, math.ceil(round(n * per * (1 + EXTRA), 6))
