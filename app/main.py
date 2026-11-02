"""The FastAPI app (PLAN-app.md §2): server-rendered Jinja2 pages, static files, the health page.
create_app(settings) builds the app; `python -m app` serves it."""
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import health, settings as S

HERE = os.path.dirname(os.path.abspath(__file__))


def create_app(settings=None):
    settings = settings or S.load()
    app = FastAPI(title="BSG Hoarding", docs_url=None, redoc_url=None, openapi_url=None)   # no API docs pages: an app, not an API
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
    templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse(request, "index.html", {"settings": settings})

    def report():
        cs = health.checks(settings)
        return cs, all(c.ok for c in cs)

    @app.get("/health", response_class=HTMLResponse)
    def health_page(request: Request):
        cs, ok = report()
        return templates.TemplateResponse(request, "health.html", {"settings": settings, "checks": cs, "ok": ok},
                                          status_code=200 if ok else 503)

    @app.get("/health.json")
    def health_json():
        cs, ok = report()
        return JSONResponse({"status": "ok" if ok else "failing",
                             "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in cs],
                             "data_dir": str(settings.data_dir), "model": settings.ai.model, "ai_enabled": settings.ai.enabled},
                            status_code=200 if ok else 503)

    return app
