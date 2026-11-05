"""Approve new drawings/documents: run the reference jobs into out/<Job>/ and rewrite the baseline.

Usage (from the repo root):
  python tests/update_baseline.py [Job ...]               rewrite expected/<Job>/baseline.json and this OS's PNGs in
                                                          expected/<Job>/png/<os>/
  python tests/update_baseline.py --store-pngs [Job ...]  only store this OS's PNGs in expected/<Job>/png/<os>/, and only
                                                          those whose pixel hash matches the approved hash in baseline.json
  python tests/update_baseline.py --store-pngs --checked [Job ...]
                                                          also store the PNGs that differ from that hash, after comparing
                                                          them by eye with the other OS's images (baseline.json stays as it is)
Default: all reference jobs. Every form writes PNGs only to the folder of the OS it runs on. Only run the first form
after checking the new PNGs and PDFs in out/<Job>/ by eye, and commit the changes with a note saying what changed and why.
"""
import os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baseline


def store(job, work, names, prune=False):
    """Copy the PNGs to this OS's folder. prune: also remove the ones it holds that are not in names."""
    if not names:
        return
    d = baseline.png_dir(job)
    os.makedirs(d, exist_ok=True)
    if prune:
        for n in os.listdir(d):
            if n.endswith(".png") and n not in names:
                os.remove(os.path.join(d, n))
    for n in names:
        shutil.copyfile(os.path.join(work, n), os.path.join(d, n))


if __name__ == "__main__":
    args = sys.argv[1:]
    only_pngs, checked = "--store-pngs" in args, "--checked" in args
    if checked and not only_pngs:
        sys.exit("--checked only goes with --store-pngs")
    jobs = [a for a in args if a not in ("--store-pngs", "--checked")] or baseline.JOBS
    bad = 0
    for job in jobs:
        work = os.path.join(baseline.ROOT, "out", job)
        baseline.run_into(job, work)
        new = baseline.snapshot(work)
        old = baseline.load(job) if os.path.exists(baseline.path(job)) else {"png": {}, "pdf": {}}
        if only_pngs:
            same = [n for n in new["png"] if old["png"].get(n) == new["png"][n]]
            diff = sorted(set(new["png"]) - set(same))
            store(job, work, sorted(new["png"]) if checked else same)
            if checked:
                print(f"{job}: stored {len(new['png'])} PNG(s) in {baseline.png_dir(job)}"
                      + (f", {len(diff)} checked by eye: {', '.join(diff)}" if diff else ""))
                continue
            bad += len(diff)
            print(f"{job}: stored {len(same)} PNG(s) identical to the approved hash in {baseline.png_dir(job)}"
                  + (f"; NOT stored (differ from the approved hash): {', '.join(diff)}. Compare them by eye "
                     f"(out/{job}/ against the other OS's images), then run: python tests/update_baseline.py --store-pngs --checked {job}" if diff else ""))
            continue
        changed = [n for kind in ("png", "pdf") for n in sorted(set(new[kind]) | set(old[kind])) if new[kind].get(n) != old[kind].get(n)]
        baseline.save(job, new)
        store(job, work, sorted(new["png"]), prune=True)
        print(f"{job}: {', '.join(changed) if changed else 'no change'}   (outputs in {work})")
    sys.exit(1 if bad else 0)
