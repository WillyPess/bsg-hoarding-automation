import os, sys

import pytest

TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS)
sys.path.insert(0, os.path.join(os.path.dirname(TESTS), "hoarding"))
import baseline


@pytest.fixture(scope="session")
def reference_run(tmp_path_factory):
    """run(job) -> (run_job summary, output folder). Each reference job runs once per session (about 5 s each)."""
    done = {}

    def run(job):
        if job not in done:
            work = str(tmp_path_factory.mktemp(job) / job)
            done[job] = (baseline.run_into(job, work), work)
        return done[job]
    return run
