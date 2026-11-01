"""Approve new drawings/documents: run the reference jobs into out/<Job>/ and rewrite the baseline.

Usage (from the repo root):
  python tests/update_baseline.py [Job ...]               rewrite expected/<Job>/baseline.json and expected/<Job>/png/
  python tests/update_baseline.py --store-pngs [Job ...]  only store the PNGs in expected/<Job>/png/, and only those
                                                          whose pixel hash matches the approved hash in baseline.json
                                                          (one-off: saves the approved Windows drawings as images)
Default: all reference jobs. Only run the first form after checking the new PNGs and PDFs in out/<Job>/ by eye,
and commit the changes with a note saying what changed and why.
"""
import os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baseline


def store(job, work, names):
    d = baseline.png_dir(job)
    os.makedirs(d, exist_ok=True)
    for n in os.listdir(d):
        if n.endswith(".png") and n not in names:
            os.remove(os.path.join(d, n))
    for n in names:
        shutil.copyfile(os.path.join(work, n), os.path.join(d, n))


if __name__ == "__main__":
    args = sys.argv[1:]
    only_pngs = "--store-pngs" in args
    jobs = [a for a in args if a != "--store-pngs"] or baseline.JOBS
    bad = 0
    for job in jobs:
        work = os.path.join(baseline.ROOT, "out", job)
        baseline.run_into(job, work)
        new = baseline.snapshot(work)
        old = baseline.load(job) if os.path.exists(baseline.path(job)) else {"png": {}, "pdf": {}}
        if only_pngs:
            ok = [n for n in new["png"] if old["png"].get(n) == new["png"][n]]
            diff = sorted(set(new["png"]) - set(ok))
            store(job, work, ok)
            bad += len(diff)
            print(f"{job}: stored {len(ok)} PNG(s) identical to the approved hash"
                  + (f"; NOT stored (differ from the approved hash): {', '.join(diff)}" if diff else ""))
            continue
        changed = [n for kind in ("png", "pdf") for n in sorted(set(new[kind]) | set(old[kind])) if new[kind].get(n) != old[kind].get(n)]
        baseline.save(job, new)
        store(job, work, sorted(new["png"]))
        print(f"{job}: {', '.join(changed) if changed else 'no change'}   (outputs in {work})")
    sys.exit(1 if bad else 0)
