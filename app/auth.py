"""Login, sessions, CSRF and the login rate limit (PLAN-app.md §9; §11 step 2).

- Passwords: hashlib.scrypt with a random salt, stored as "scrypt$n$r$p$salt$hash" (base64). Checked in constant time.
- Sessions live on the server: the cookie holds a random id, the database keeps its sha256. Logout deletes the row,
  so an old cookie stops working at once. A session ends after IDLE_TIMEOUT without use, or MAX_AGE in all.
- CSRF: every form carries csrf_token. Logged in: the session's own token. On the login page (no session yet): a
  token also set in the bsg_csrf cookie (double submit). A POST without the right token is refused (403) before
  the route runs; the check is a dependency on the whole app, so a new form can't forget it.
- Rate limit: after MAX_FAILURES failed logins for one name, or from one address, within LOCKOUT, logins are
  refused (429) until LOCKOUT has passed. On this PC every request comes from 127.0.0.1, so the address limit
  locks both users; that is the price of stopping someone guessing many names."""
import base64, hashlib, hmac, secrets, time
from urllib.parse import quote

from fastapi import HTTPException, Request

from app import db
from app.users import User

IDLE_TIMEOUT = 12 * 3600
MAX_AGE = 7 * 24 * 3600
MAX_FAILURES = 5
LOCKOUT = 15 * 60
SESSION_COOKIE = "bsg_session"
CSRF_COOKIE = "bsg_csrf"
PUBLIC = ("/login",)
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1


def now():
    return time.time()


# --- passwords --------------------------------------------------------------------------------------------------------

def _b64(b):
    return base64.b64encode(b).decode("ascii")


def hash_password(password):
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(h)}"


def verify_password(password, stored):
    try:
        kind, n, r, p, salt, h = stored.split("$")
        if kind != "scrypt":
            return False
        want = base64.b64decode(h)
        got = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(want))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, want)


DUMMY_HASH = hash_password(secrets.token_hex(16))   # checked for unknown names, so they take as long as real ones


# --- sessions ---------------------------------------------------------------------------------------------------------

def _sha(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def start_session(conn, user_id):
    """A new session (new id on every login: a planted cookie is never reused). Returns the cookie value."""
    token = secrets.token_urlsafe(32)
    t = now()
    with conn:
        conn.execute("INSERT INTO sessions (id_hash, user_id, csrf, created_at, last_seen) VALUES (?, ?, ?, ?, ?)",
                     (_sha(token), user_id, secrets.token_urlsafe(32), t, t))
    return token


def load_session(conn, token):
    """(User, csrf token) for a live session, or None. Expired sessions are deleted; a live one is touched."""
    if not token:
        return None
    t = now()
    with conn:
        conn.execute("DELETE FROM sessions WHERE last_seen < ? OR created_at < ?", (t - IDLE_TIMEOUT, t - MAX_AGE))
        row = conn.execute("SELECT s.csrf, u.id, u.name, u.role FROM sessions s JOIN users u ON u.id = s.user_id "
                           "WHERE s.id_hash = ? AND u.active = 1", (_sha(token),)).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE sessions SET last_seen = ? WHERE id_hash = ?", (t, _sha(token)))
    return User(row["id"], row["name"], row["role"]), row["csrf"]


def end_session(conn, token):
    with conn:
        conn.execute("DELETE FROM sessions WHERE id_hash = ?", (_sha(token or ""),))


# --- rate limit -------------------------------------------------------------------------------------------------------

def _failures(conn, column, value, t):
    last_ok = conn.execute(f"SELECT MAX(at) FROM login_attempts WHERE {column} = ? AND ok = 1", (value,)).fetchone()[0] or 0
    return conn.execute(f"SELECT COUNT(*) FROM login_attempts WHERE {column} = ? AND ok = 0 AND at > ?",
                        (value, max(t - LOCKOUT, last_ok))).fetchone()[0]


def locked(conn, name, ip):
    t = now()
    return _failures(conn, "name", name, t) >= MAX_FAILURES or _failures(conn, "ip", ip, t) >= MAX_FAILURES


def record_attempt(conn, name, ip, ok):
    with conn:
        conn.execute("INSERT INTO login_attempts (name, ip, ok, at) VALUES (?, ?, ?, ?)", (name, ip, int(ok), now()))


def client_ip(request):
    return request.client.host if request.client else "unknown"


# --- dependencies on every route -------------------------------------------------------------------------------------

def safe_next(next_):
    """Only a path on this site: no scheme, no //host, no /\\host (open redirect)."""
    if not next_ or not next_.startswith("/") or next_.startswith(("//", "/\\")):
        return "/"
    return next_


async def require_user(request: Request):
    """Sets request.state.user / .csrf from the session cookie; sends anyone not logged in to /login."""
    settings = request.app.state.settings
    conn = db.connect(settings)
    try:
        found = load_session(conn, request.cookies.get(SESSION_COOKIE))
    finally:
        conn.close()
    request.state.user, request.state.csrf = found if found else (None, None)
    if found is None and request.url.path not in PUBLIC:
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        raise HTTPException(status_code=303, headers={"Location": "/login?next=" + quote(target, safe="")})


async def csrf_guard(request: Request):
    """Refuses (403) any POST whose csrf_token isn't this session's token (the login page's cookie token on /login)."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    form = await request.form()
    sent = form.get("csrf_token") or ""
    expected = request.cookies.get(CSRF_COOKIE) if request.url.path == "/login" else request.state.csrf
    if not (isinstance(sent, str) and expected and hmac.compare_digest(sent, expected)):
        raise HTTPException(status_code=403, detail="This form has expired or did not come from this app. Go back, reload the page and try again.")
