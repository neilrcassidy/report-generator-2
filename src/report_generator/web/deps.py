"""FastAPI dependencies and template rendering helpers."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from report_generator.config import AppConfig

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


SessionDep = Annotated[Session, Depends(get_session)]
ConfigDep = Annotated[AppConfig, Depends(get_config)]


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def render(
    request: Request, template: str, context: dict[str, Any], status_code: int = 200
) -> HTMLResponse:
    context = {"config": request.app.state.config, **context}
    return templates.TemplateResponse(request, template, context, status_code=status_code)
