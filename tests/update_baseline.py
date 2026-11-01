"""Approve new drawings/documents: run the reference jobs into out/<Job>/ and rewrite expected/<Job>/baseline.json.

Usage (from the repo root):  python tests/update_baseline.py [Job ...]     (default: all reference jobs)
Only run this after checking the new PNGs and PDFs in out/<Job>/ by eye. Commit the baseline.json changes
with a note saying what changed and why.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baseline

if __name__ == "__main__":
    for job in sys.argv[1:] or baseline.JOBS:
        work = os.path.join(baseline.ROOT, "out", job)
        baseline.run_into(job, work)
        new = baseline.snapshot(work)
        old = baseline.load(job) if os.path.exists(baseline.path(job)) else {"png": {}, "pdf": {}}
        changed = [n for kind in ("png", "pdf") for n in sorted(set(new[kind]) | set(old[kind])) if new[kind].get(n) != old[kind].get(n)]
        baseline.save(job, new)
        print(f"{job}: {', '.join(changed) if changed else 'no change'}   (outputs in {work})")
