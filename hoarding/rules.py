"""BSG business values from rules.json: sheet and door sizes, spares, weight matrix, external-job rule, defaults, rate card.
Each entry in rules.json is {"value", "source", "provisional"}; RULES keeps only the values, e.g. RULES["sheet"]["width"] = 1.2."""
import json, os


def _values(x):
    if isinstance(x, dict):
        return _values(x["value"]) if "value" in x else {k: _values(v) for k, v in x.items() if not k.startswith("_")}
    return x


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json"), encoding="utf-8") as f:
    RULES = _values(json.load(f))
