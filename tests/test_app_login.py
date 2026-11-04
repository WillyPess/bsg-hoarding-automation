"""Users and login (PLAN-app.md §3, §9; §11 step 2): two users with roles, scrypt password hashes, server-side
sessions, a CSRF token on every form, a login rate limit, logout, and `python -m app.users`."""
import os, sqlite3, subprocess, sys
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

import app_helpers as H
from app import auth, settings as S, users
from app.main import create_app


@pytest.fixture
def data(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def app_and_settings(data):
    return H.make_app(data)


@pytest.fixture
def anon(app_and_settings):
    return TestClient(app_and_settings[0])


# --- password hashes --------------------------------------------------------------------------------------------------

def test_scrypt_hash_and_verify():
    h = auth.hash_password("correct horse battery")
    assert h.startswith("scrypt$") and "correct" not in h
    assert auth.verify_password("correct horse battery", h)
    assert not auth.verify_password("correct horse batterY", h)
    assert auth.hash_password("correct horse battery") != h          # a new salt every time


def test_verify_refuses_a_broken_hash():
    assert not auth.verify_password("x", "plain-text")
    assert not auth.verify_password("x", "")


# --- users ------------------------------------------------------------------------------------------------------------

def test_two_users_with_roles(app_and_settings):
    _, s = app_and_settings
    assert [(u.name, u.role) for u in users.all_users(s)] == [("boss", "manager"), ("gus", "estimator")]


@pytest.mark.parametrize("name, role, password, word", [
    ("Gus", "estimator", H.PASSWORD, "already"),            # names are unique, not case-sensitive
    ("anna", "admin", H.PASSWORD, "role"),
    ("anna", "estimator", "short", "10"),
    ("", "estimator", H.PASSWORD, "name"),
    ("a b", "estimator", H.PASSWORD, "name"),
])
def test_bad_user(app_and_settings, name, role, password, word):
    _, s = app_and_settings
    with pytest.raises(users.UserError, match=word):
        users.add(s, name, role, password)


def test_set_password(app_and_settings, anon):
    _, s = app_and_settings
    users.set_password(s, "gus", "a brand new password")
    assert H.login(anon, "gus").status_code == 401
    assert H.login(anon, "gus", "a brand new password").status_code == 303


def test_password_hash_is_stored_not_the_password(app_and_settings, data):
    with closing(sqlite3.connect(data / "bsg.sqlite")) as conn:
        rows = conn.execute("SELECT password_hash FROM users").fetchall()
    assert rows and all(r[0].startswith("scrypt$") and H.PASSWORD not in r[0] for r in rows)


def users_cli(*args, data, stdin=None):
    env = {**os.environ, "BSG_DATA": str(data)}
    return subprocess.run([sys.executable, "-m", "app.users", *args], cwd=H.ROOT, env=env, input=stdin,
                          capture_output=True, text=True, timeout=60)


def test_cli_add_list_set_password(data):
    r = users_cli("add", "gus", "--role", "estimator", "--password-stdin", data=data, stdin="correct horse battery\n")
    assert r.returncode == 0, r.stderr
    r = users_cli("add", "boss", "--role", "manager", "--password-stdin", data=data, stdin="another long password\n")
    assert r.returncode == 0, r.stderr
    r = users_cli("list", data=data)
    assert "gus" in r.stdout and "estimator" in r.stdout and "boss" in r.stdout and "manager" in r.stdout
    assert "scrypt" not in r.stdout
    r = users_cli("set-password", "gus", "--password-stdin", data=data, stdin="a third long password\n")
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("args, stdin, word", [
    (("add", "gus", "--role", "boss", "--password-stdin"), "correct horse battery\n", "role"),
    (("add", "gus", "--role", "estimator", "--password-stdin"), "short\n", "10"),
    (("set-password", "nobody", "--password-stdin"), "correct horse battery\n", "nobody"),
])
def test_cli_errors(data, args, stdin, word):
    r = users_cli(*args, data=data, stdin=stdin)
    assert r.returncode != 0 and word in (r.stderr + r.stdout)


def test_cli_add_twice(data):
    users_cli("add", "gus", "--role", "estimator", "--password-stdin", data=data, stdin="correct horse battery\n")
    r = users_cli("add", "GUS", "--role", "manager", "--password-stdin", data=data, stdin="correct horse battery\n")
    assert r.returncode != 0 and "already" in r.stderr


# --- login required ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/", "/health", "/health.json"])
def test_pages_need_login(anon, path):
    r = anon.get(path, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


def test_login_page_and_static_are_public(anon):
    assert anon.get("/login").status_code == 200
    assert anon.get("/static/style.css").status_code == 200


def test_login_page_says_how_to_add_users_when_there_are_none(data):
    c = TestClient(create_app(S.load(data)))
    assert "python -m app.users add" in c.get("/login").text


def test_login_and_logout(anon):
    r = H.login(anon, next_="/health")
    assert r.status_code == 303 and r.headers["location"] == "/health"
    cookie = r.headers["set-cookie"].lower()
    assert "bsg_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    home = anon.get("/")
    assert home.status_code == 200 and "gus" in home.text and "estimator" in home.text
    r = anon.post("/logout", data={"csrf_token": H.csrf_from(home.text)}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert anon.get("/", follow_redirects=False).status_code == 303


def test_logout_ends_the_session_on_the_server(anon, data):
    H.login(anon)
    sid = anon.cookies.get("bsg_session")
    home = anon.get("/")
    anon.post("/logout", data={"csrf_token": H.csrf_from(home.text)})
    stolen = TestClient(anon.app, cookies={"bsg_session": sid})       # the old cookie is worthless after logout
    assert stolen.get("/", follow_redirects=False).status_code == 303


def test_boss_logs_in_too(app_and_settings):
    c = H.logged_in(app_and_settings[0], "boss")
    assert "boss" in c.get("/").text and "manager" in c.get("/").text


@pytest.mark.parametrize("name, password", [("gus", "wrong password!!"), ("nobody", H.PASSWORD), ("GUS", H.PASSWORD + "x")])
def test_wrong_login(anon, name, password):
    r = H.login(anon, name, password)
    assert r.status_code == 401
    assert "Wrong name or password" in r.text                       # the same message: it doesn't say which was wrong
    assert anon.get("/", follow_redirects=False).status_code == 303


def test_name_is_not_case_sensitive(anon):
    assert H.login(anon, "GUS").status_code == 303


@pytest.mark.parametrize("next_", ["https://evil.example/", "//evil.example/", "javascript:alert(1)", "/\\evil.example"])
def test_no_open_redirect_after_login(anon, next_):
    r = H.login(anon, next_=next_)
    assert r.status_code == 303 and r.headers["location"] == "/"


def test_new_session_id_on_login(anon):
    # session fixation: a planted id is never turned into a session; login sets a new, random one
    planted = TestClient(anon.app, cookies={"bsg_session": "attacker-chosen-id"})
    r = H.login(planted)
    new = r.cookies.get("bsg_session")
    assert new and new != "attacker-chosen-id" and len(new) >= 40
    assert TestClient(anon.app, cookies={"bsg_session": "attacker-chosen-id"}).get("/", follow_redirects=False).status_code == 303


def test_session_expires_when_idle(anon, monkeypatch):
    H.login(anon)
    t = auth.now()
    monkeypatch.setattr(auth, "now", lambda: t + auth.IDLE_TIMEOUT + 1)
    assert anon.get("/", follow_redirects=False).status_code == 303


def test_session_expires_after_the_maximum_age(anon, monkeypatch):
    H.login(anon)
    t0 = auth.now()
    for hours in range(1, 24 * 8, 6):                                 # active every 6 hours, but not past 7 days
        monkeypatch.setattr(auth, "now", lambda h=hours: t0 + h * 3600)
        r = anon.get("/", follow_redirects=False)
    assert r.status_code == 303


# --- CSRF on every form -----------------------------------------------------------------------------------------------

def post_routes(app):
    return sorted({r.path for r in app.routes if "POST" in getattr(r, "methods", set())})


def test_every_post_route_refuses_a_missing_or_wrong_csrf_token(app_and_settings):
    app = app_and_settings[0]
    paths = post_routes(app)
    assert {"/login", "/logout"} <= set(paths)
    c = H.logged_in(app)
    for path in paths:
        for data in ({}, {"csrf_token": "wrong"}):
            r = c.post(path, data=data, follow_redirects=False)
            assert r.status_code == 403, (path, data, r.status_code)
    assert c.get("/", follow_redirects=False).status_code == 200      # still logged in: nothing happened


def test_every_page_form_carries_the_csrf_token(app_and_settings):
    c = H.logged_in(app_and_settings[0])
    for path in ("/", "/health"):
        html = c.get(path).text
        assert html.count("<form") == html.count('name="csrf_token"'), path


def test_login_needs_the_token_from_the_login_page(anon):
    anon.get("/login")
    r = anon.post("/login", data={"name": "gus", "password": H.PASSWORD, "csrf_token": "made-up"}, follow_redirects=False)
    assert r.status_code == 403


def test_csrf_token_belongs_to_the_session(app_and_settings):
    a, b = H.logged_in(app_and_settings[0], "gus"), H.logged_in(app_and_settings[0], "boss")
    token_b = H.csrf_from(b.get("/").text)
    assert a.post("/logout", data={"csrf_token": token_b}, follow_redirects=False).status_code == 403


# --- rate limit -------------------------------------------------------------------------------------------------------

def test_limits():
    # decided 2026-11-03: 5 failures per name, 20 per address (both users come from 127.0.0.1 on this PC)
    assert (auth.MAX_FAILURES, auth.MAX_FAILURES_PER_ADDRESS, auth.LOCKOUT) == (5, 20, 15 * 60)


def test_rate_limit_after_5_failures(anon):
    for _ in range(auth.MAX_FAILURES):
        assert H.login(anon, "gus", "wrong password!!").status_code == 401
    r = H.login(anon, "gus")                                          # even the right password is refused for now
    assert r.status_code == 429 and "Too many" in r.text


def test_one_persons_typos_dont_lock_the_other_out(anon):
    for _ in range(auth.MAX_FAILURES):
        H.login(anon, "gus", "wrong password!!")
    assert H.login(anon, "gus").status_code == 429                   # gus waits 15 minutes
    assert H.login(anon, "boss").status_code == 303                  # the boss, from the same 127.0.0.1, still gets in


def test_rate_limit_counts_unknown_names_from_the_same_address(anon):
    # guessing many names: 4 tries each (under the per-name limit), but 20 from one address lock that address
    for i in range(auth.MAX_FAILURES_PER_ADDRESS):
        assert H.login(anon, f"nobody{i // 4}", "wrong password!!").status_code == 401
    assert H.login(anon, "boss").status_code == 429


def test_address_limit_is_not_reached_at_19(anon):
    for i in range(auth.MAX_FAILURES_PER_ADDRESS - 1):
        H.login(anon, f"nobody{i // 4}", "wrong password!!")
    assert H.login(anon, "boss").status_code == 303


def test_rate_limit_lifts_after_the_lockout(anon, monkeypatch):
    for _ in range(auth.MAX_FAILURES):
        H.login(anon, "gus", "wrong password!!")
    t = auth.now()
    monkeypatch.setattr(auth, "now", lambda: t + auth.LOCKOUT + 1)
    assert H.login(anon, "gus").status_code == 303


def test_failed_logins_are_recorded(anon, data):
    H.login(anon, "gus", "wrong password!!")
    H.login(anon, "gus")
    with closing(sqlite3.connect(data / "bsg.sqlite")) as conn:
        rows = conn.execute("SELECT name, ok FROM login_attempts ORDER BY id").fetchall()
    assert rows == [("gus", 0), ("gus", 1)]


# --- pages ------------------------------------------------------------------------------------------------------------

def test_password_never_in_a_page(anon):
    r = H.login(anon, "gus", "wrong password!!")
    assert "wrong password!!" not in r.text


def test_security_headers(anon):
    h = anon.get("/login").headers
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff"
