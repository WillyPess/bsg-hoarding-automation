"""App skeleton (PLAN-app.md §11 step 1): the app/ package, FastAPI, base template, static files, settings
(BSG_DATA, config.toml), `python -m app` and the health page. No jobs, login or AI yet."""
import os, re, subprocess, sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import settings as S
from app.main import create_app


@pytest.fixture
def data(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def client(data):
    # pages need a login since step 2 (test_app_login.py)
    import app_helpers as H
    return H.logged_in(H.make_app(data)[0])


# --- settings ---------------------------------------------------------------------------------------------------------

def test_data_dir_from_bsg_data(monkeypatch, tmp_path):
    monkeypatch.setenv("BSG_DATA", str(tmp_path / "x"))
    assert S.load().data_dir == tmp_path / "x"


def test_default_data_dir(monkeypatch):
    # PLAN-app.md §7: C:\BSG\data on Gus's Windows PC; ~/BSG/data elsewhere (Linux, CI)
    monkeypatch.delenv("BSG_DATA", raising=False)
    expected = Path(r"C:\BSG\data") if os.name == "nt" else Path.home() / "BSG" / "data"
    assert S.default_data_dir() == expected
    assert S.load.__defaults__ == (None,)   # load() with no folder uses BSG_DATA, then this default


def test_defaults_without_config_toml(data):
    s = S.load(data)
    assert (s.host, s.port) == ("127.0.0.1", 8000)
    assert (s.ai.model, s.ai.effort, s.ai.cap_per_job_usd, s.ai.cap_per_month_usd) == ("claude-opus-5-5", "medium", 1.0, 60.0)
    assert s.ai.enabled is False   # the AI reviewer comes in later PRs (§11 steps 9-12)


def test_first_load_creates_the_data_folder_and_a_config_toml(data):
    S.load(data)
    assert (data / "config.toml").is_file()
    text = (data / "config.toml").read_text(encoding="utf-8")
    assert 'model = "claude-opus-5-5"' in text and "cap_per_job_usd = 1.0" in text
    assert S.load(data) == S.load(data)   # loading again reads the same file back


def test_config_toml_overrides(data):
    data.mkdir(parents=True)
    (data / "config.toml").write_text('[server]\nport = 8123\n[ai]\ncap_per_job_usd = 2.5\n', encoding="utf-8")
    s = S.load(data)
    assert (s.port, s.ai.cap_per_job_usd, s.ai.cap_per_month_usd) == (8123, 2.5, 60.0)


@pytest.mark.parametrize("toml, word", [
    ('[server]\nhost = "0.0.0.0"\n', "127.0.0.1"),          # v1 listens on this PC only (§9)
    ('[server]\nport = 0\n', "port"),
    ('[ai]\ncap_per_job_usd = -1\n', "cap_per_job_usd"),
    ('[ai]\neffort = "huge"\n', "effort"),
    ('[ai]\nmodle = "x"\n', "modle"),                        # a typo is an error, not ignored
    ('[wat]\nx = 1\n', "wat"),
    ('[ai]\nfallback = true\n', "fallback"),                 # no refusal fallback: strictly one model (§8.7)
    ('[server\n', "config.toml"),                            # broken TOML
])
def test_bad_config_is_refused(data, toml, word):
    data.mkdir(parents=True)
    (data / "config.toml").write_text(toml, encoding="utf-8")
    with pytest.raises(S.ConfigError, match=re.escape(word)):
        S.load(data)


def test_no_secrets_in_config(data):
    s = S.load(data)
    import tomllib
    raw = tomllib.loads((data / "config.toml").read_text(encoding="utf-8"))
    keys = [k.lower() for table in raw.values() for k in table]   # settings, not the comments explaining where secrets live
    assert not [k for k in keys if any(w in k for w in ("key", "password", "secret", "token"))]
    assert not hasattr(s.ai, "api_key")


# --- pages ------------------------------------------------------------------------------------------------------------

def test_home_page_uses_the_base_template(client):
    r = client.get("/")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "<title>" in r.text and "BSG Hoarding" in r.text
    assert '/static/style.css' in r.text
    assert 'href="/health"' in r.text


def test_static_files(client):
    r = client.get("/static/style.css")
    assert r.status_code == 200 and "text/css" in r.headers["content-type"]
    assert "body" in r.text


def test_no_cdn(client):
    # everything works offline: no stylesheet or script from another site (§2)
    html = client.get("/").text + client.get("/health").text + client.get("/login").text
    assert not re.search(r'(src|href)="(https?:)?//', html)


def test_health_page(client, data):
    r = client.get("/health")
    assert r.status_code == 200
    for name in ("Data folder", "config.toml", "Engine rules", "LibreOffice", "Fonts"):
        assert name in r.text
    assert str(data) in r.text


def test_health_json(client, data):
    r = client.get("/health.json")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    names = {c["name"] for c in j["checks"]}
    assert {"Data folder", "config.toml", "Engine rules", "LibreOffice", "Fonts"} <= names
    assert all(c["ok"] for c in j["checks"])
    assert j["model"] == "claude-opus-5-5" and j["ai_enabled"] is False


def test_health_reports_a_failing_check(client, monkeypatch):
    from app import health
    monkeypatch.setattr(health, "soffice_path", lambda: None)
    r = client.get("/health.json")
    assert r.status_code == 503
    j = r.json()
    assert j["status"] == "failing"
    [lo] = [c for c in j["checks"] if c["name"] == "LibreOffice"]
    assert lo["ok"] is False and lo["detail"]


def test_unknown_page_is_404(client):
    assert client.get("/nope").status_code == 404


# --- python -m app ----------------------------------------------------------------------------------------------------

def run_app(*args, data):
    env = {**os.environ, "BSG_DATA": str(data)}
    return subprocess.run([sys.executable, "-m", "app", *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)


def test_python_m_app_check(data):
    r = run_app("--check", data=data)
    assert r.returncode == 0, r.stderr
    assert "Data folder" in r.stdout and "ok" in r.stdout
    assert "http://127.0.0.1:8000" in r.stdout


def test_python_m_app_refuses_bad_config(data):
    data.mkdir(parents=True)
    (data / "config.toml").write_text('[server]\nhost = "0.0.0.0"\n', encoding="utf-8")
    r = run_app("--check", data=data)
    assert r.returncode != 0 and "127.0.0.1" in (r.stderr + r.stdout)


# --- the app never calculates -----------------------------------------------------------------------------------------

def test_app_does_not_import_the_engine_calculations():
    # PLAN-app.md §10: only the engine bridge (a later PR) may call run_job; no app module imports the calculators
    bad = re.compile(r"^\s*(from|import)\s+(hoarding\.)?(layout_gen|titan|tape|materials|package_gen|quote_gen|cutplan)\b", re.M)
    for dirpath, _, files in os.walk(os.path.join(ROOT, "app")):
        for f in files:
            if f.endswith(".py"):
                with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                    text = fh.read()
                assert not bad.search(text), f"{f} imports an engine calculation module"
