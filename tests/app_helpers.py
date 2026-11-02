"""Shared helpers for the app tests: a data folder with users, and a logged-in TestClient."""
import os, re, sys

from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import settings as S, users
from app.main import create_app

PASSWORD = "correct horse battery"


def make_app(data, people=(("gus", "estimator"), ("boss", "manager"))):
    s = S.load(data)
    for name, role in people:
        users.add(s, name, role, PASSWORD)
    return create_app(s), s


def csrf_from(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "no csrf_token field on the page"
    return m.group(1)


def login(client, name="gus", password=PASSWORD, next_="/"):
    page = client.get("/login")
    return client.post("/login", data={"name": name, "password": password, "next": next_, "csrf_token": csrf_from(page.text)},
                       follow_redirects=False)


def logged_in(app, name="gus"):
    c = TestClient(app)
    r = login(c, name)
    assert r.status_code == 303, r.text
    return c
