"""A hand-set "uprights" in job.json (corners that can't take uprights, Gus 2026-10-28) reaches every output, not only the materials form."""
import json, os, shutil

import baseline, run_job, titan
from check_fixtures import pdf_text


def test_package_uses_hand_set_uprights(tmp_path):
    # Bikini: the layout has 10 uprights (7 weights each at 4.5 m, 77 sent). Set 12 by hand: 12 x 7 x 1.1 = 92.4 -> 93.
    work = str(tmp_path / "Bikini")
    shutil.copytree(os.path.join(baseline.ROOT, "hoarding", "Bikini"), work)
    jp = os.path.join(work, "job.json")
    job = json.load(open(jp))
    json.dump({**job, "uprights": 12}, open(jp, "w"))

    s = run_job.run(work)
    assert (s["uprights_at_joins"], s["uprights_to_send"], s["weights_to_send"]) == (12, 12, 93)
    assert titan.for_job(job, 12) == (12, 0, 7, 93)

    text = " ".join(pdf_text(os.path.join(work, "Bikini_Hoarding_Package.pdf"))[1])
    assert "12 uprights, each one at a joint" in text
    assert "93 sent" in text and "77 sent" not in text
