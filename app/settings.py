"""App settings (PLAN-app.md §7, §8.7, §9).

The data folder comes from BSG_DATA (default C:\\BSG\\data on Windows, ~/BSG/data elsewhere). It holds config.toml:
server address and AI settings, no secrets (the API key comes from ANTHROPIC_API_KEY; sessions live in
bsg.sqlite and need no key). The first load creates the folder and writes a config.toml with the defaults, so Gus
can see and edit every setting. Unknown keys and bad values are refused, so a typo can't be silently ignored."""
import ipaddress, os, tomllib
from dataclasses import dataclass, field
from pathlib import Path

MODEL = "claude-opus-5-5"   # pinned (§8.7); changing it is its own PR with the recorded tests re-run
EFFORTS = ("low", "medium", "high", "xhigh", "max")


class ConfigError(ValueError):
    """config.toml can't be used; the message says which key and why."""


@dataclass(frozen=True)
class AISettings:
    enabled: bool = False          # the AI reviewer arrives in §11 steps 9-12; off until then
    model: str = MODEL
    effort: str = "medium"
    cap_per_job_usd: float = 1.0   # decided 2026-11-02 (§14): all of one job's AI calls
    cap_per_month_usd: float = 60.0


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 8000
    ai: AISettings = field(default_factory=AISettings)

    @property
    def config_path(self):
        return self.data_dir / "config.toml"

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"


DEFAULT_TOML = f'''# BSG Hoarding app settings (PLAN-app.md). No secrets here:
# the Claude API key comes from the ANTHROPIC_API_KEY environment variable.

[server]
# v1 listens on this PC only (127.0.0.1); Cloudflare Tunnel comes later (PLAN-app.md §9).
host = "127.0.0.1"
port = 8000

[ai]
# The AI reviewer (PLAN-app.md §8). Off until it is built.
enabled = false
# One pinned model, no refusal fallback (decided 2026-11-02).
model = "{MODEL}"
effort = "medium"
# Cost caps in USD (decided 2026-11-02): all of one job's AI calls, and each calendar month.
cap_per_job_usd = 1.0
cap_per_month_usd = 60.0
'''


def default_data_dir():
    return Path(r"C:\BSG\data") if os.name == "nt" else Path.home() / "BSG" / "data"


def _check_keys(table, allowed, where):
    unknown = set(table) - set(allowed)
    if unknown:
        raise ConfigError(f"config.toml [{where}]: unknown setting(s) {', '.join(sorted(unknown))}")


def _number(value, key, minimum=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
        raise ConfigError(f"config.toml: {key} must be a number of at least {minimum:g}, not {value!r}")
    return float(value)


def load(data_dir=None):
    """Settings from <data_dir>/config.toml (data_dir: argument, else BSG_DATA, else the default folder).
    Creates the folder and a default config.toml the first time."""
    data_dir = Path(data_dir or os.environ.get("BSG_DATA") or default_data_dir())
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "config.toml"
    if not path.exists():
        path.write_text(DEFAULT_TOML, encoding="utf-8")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"config.toml ({path}) is not valid TOML: {e}") from None
    _check_keys(raw, ("server", "ai"), "top level")
    srv, ai = raw.get("server", {}), raw.get("ai", {})
    _check_keys(srv, ("host", "port"), "server")
    _check_keys(ai, ("enabled", "model", "effort", "cap_per_job_usd", "cap_per_month_usd"), "ai")

    host = srv.get("host", "127.0.0.1")
    try:
        loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    if not loopback:
        raise ConfigError(f"config.toml: server.host must be 127.0.0.1 (this PC only, PLAN-app.md §9), not {host!r}")
    port = srv.get("port", 8000)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigError(f"config.toml: server.port must be a whole number from 1 to 65535, not {port!r}")

    enabled = ai.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigError(f"config.toml: ai.enabled must be true or false, not {enabled!r}")
    model = ai.get("model", MODEL)
    if not isinstance(model, str) or not model.strip():
        raise ConfigError("config.toml: ai.model must be a model ID")
    effort = ai.get("effort", "medium")
    if effort not in EFFORTS:
        raise ConfigError(f"config.toml: ai.effort must be one of {', '.join(EFFORTS)}, not {effort!r}")
    return Settings(data_dir=data_dir, host=host, port=port, ai=AISettings(
        enabled=enabled, model=model, effort=effort,
        cap_per_job_usd=_number(ai.get("cap_per_job_usd", 1.0), "ai.cap_per_job_usd"),
        cap_per_month_usd=_number(ai.get("cap_per_month_usd", 60.0), "ai.cap_per_month_usd")))
