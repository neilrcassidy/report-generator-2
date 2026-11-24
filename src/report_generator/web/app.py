"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from report_generator.config import load_config
from report_generator.db.engine import make_engine, migrate
from report_generator.pdf.report import ASSETS_DIR
from report_generator.settings import Settings
from report_generator.web.routes import reports, students

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    # Fail fast on a bad config (e.g. a certification listed in two groups).
    config = load_config(settings.config_path)

    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    migrate(settings.database_url)

    app = FastAPI(title=config.texts.title, docs_url=None, redoc_url=None)
    app.state.config = config
    app.state.engine = make_engine(settings.database_url)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    # Logo and icons shared with the PDF (single copy, in pdf/assets).
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    app.include_router(reports.router)
    app.include_router(students.router)

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse("/students")

    return app
