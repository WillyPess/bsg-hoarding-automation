"""The app's only door into the engine (PLAN-app.md §1, §6): the engine's own functions, imported from hoarding/.

Step 4 uses the input side: jobs.normalize (form inputs -> job.json, defaults from rules.json), validate.check (what
is wrong), jobs.warnings and jobs.suggest_prefix. Running the engine (run_job) comes in step 6. No app module imports
the calculators (layout_gen, titan, tape, materials, ...): every number comes from the engine."""
from app import health

health._engine_path()
import jobs as _jobs        # noqa: E402  hoarding/jobs.py
import validate as _validate  # noqa: E402  hoarding/validate.py
from rules import RULES     # noqa: E402  hoarding/rules.json (read-only here: shown as hints, never applied by the app)

normalize = _jobs.normalize
suggest_prefix = _jobs.suggest_prefix
warnings = _jobs.warnings
check = _validate.check
kind = _validate.kind
Problem = _validate.Problem

__all__ = ["normalize", "suggest_prefix", "warnings", "check", "kind", "Problem", "RULES"]
