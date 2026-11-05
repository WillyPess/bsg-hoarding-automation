"""The FastAPI app (PLAN-app.md §2): server-rendered Jinja2 pages, static files, login, the health page.
create_app(settings) builds the app; `python -m app` serves it.

Every route depends on auth.require_user (login needed except on /login) and auth.csrf_guard (every POST needs the
form's csrf_token), so a new page or form gets both without having to remember them."""
import os
import secrets

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import auth, db, health, pages_jobs, pages_runs, settings as S, storage, users

HERE = os.path.dirname(os.path.abspath(__file__))
SECURITY_HEADERS = {"X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin"}


def create_app(settings=None):
    settings = settings or S.load()
    db.connect(settings).close()   # create or update the database before the first request
    storage.interrupt_unfinished(settings)
    app = FastAPI(title="BSG Hoarding", docs_url=None, redoc_url=None, openapi_url=None,   # an app, not an API
                  dependencies=[Depends(auth.require_user), Depends(auth.csrf_guard)])
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
    templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        return response

    def page(request, name, status_code=200, **ctx):
        ctx = {"settings": settings, "user": request.state.user, "csrf": request.state.csrf, **ctx}
        return templates.TemplateResponse(request, name, ctx, status_code=status_code)

    # --- login / logout -----------------------------------------------------------------------------------------------

    def login_page(request, status_code=200, message="", next_="/"):
        token = request.cookies.get(auth.CSRF_COOKIE) or secrets.token_urlsafe(32)
        has_users = bool(users.all_users(settings))
        r = page(request, "login.html", status_code, login_csrf=token, message=message, next_=auth.safe_next(next_), has_users=has_users)
        r.set_cookie(auth.CSRF_COOKIE, token, httponly=True, samesite="strict", path="/login")
        return r

    @app.get("/login", response_class=HTMLResponse)
    def login_get(request: Request, next: str = "/"):
        if request.state.user:
            return RedirectResponse(auth.safe_next(next), status_code=303)
        return login_page(request, next_=next)

    @app.post("/login", response_class=HTMLResponse)
    async def login_post(request: Request):
        form = await request.form()
        name = str(form.get("name") or "").strip().lower()
        password = str(form.get("password") or "")
        next_ = auth.safe_next(str(form.get("next") or "/"))
        ip = auth.client_ip(request)
        conn = db.connect(settings)
        try:
            if auth.locked(conn, name, ip):
                return login_page(request, 429, f"Too many failed logins. Try again in {auth.LOCKOUT // 60} minutes.", next_)
            found = users.find(conn, name)
            ok = auth.verify_password(password, found[1] if found else auth.DUMMY_HASH) and found is not None
            auth.record_attempt(conn, name, ip, ok)
            if not ok:
                return login_page(request, 401, "Wrong name or password.", next_)
            token = auth.start_session(conn, found[0].id)
        finally:
            conn.close()
        r = RedirectResponse(next_, status_code=303)
        r.set_cookie(auth.SESSION_COOKIE, token, httponly=True, samesite="lax", path="/")   # Secure comes with the tunnel (§9)
        r.delete_cookie(auth.CSRF_COOKIE, path="/login")
        return r

    @app.post("/logout")
    def logout(request: Request):
        conn = db.connect(settings)
        try:
            auth.end_session(conn, request.cookies.get(auth.SESSION_COOKIE))
        finally:
            conn.close()
        r = RedirectResponse("/login", status_code=303)
        r.delete_cookie(auth.SESSION_COOKIE, path="/")
        return r

    # --- pages --------------------------------------------------------------------------------------------------------

    @app.get("/")
    def home():
        return RedirectResponse("/jobs", status_code=303)

    pages_jobs.add_routes(app, page, settings)
    pages_runs.add_routes(app, page, settings)

    def report():
        cs = health.checks(settings)
        return cs, all(c.ok for c in cs)

    @app.get("/health", response_class=HTMLResponse)
    def health_page(request: Request):
        cs, ok = report()
        return page(request, "health.html", 200 if ok else 503, checks=cs, ok=ok)

    @app.get("/health.json")
    def health_json():
        cs, ok = report()
        return JSONResponse({"status": "ok" if ok else "failing",
                             "checks": [{"name": c.name, "ok": c.ok, "level": c.level, "detail": c.detail} for c in cs],
                             "data_dir": str(settings.data_dir), "model": settings.ai.model, "ai_enabled": settings.ai.enabled},
                            status_code=200 if ok else 503)

    return app
