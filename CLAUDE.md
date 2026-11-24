# report-generator-2 conventions

A local web app (one PC, no auth) for entering students and their mock exam scores. It generates the Spanish "Mock Exam Report Card" PDFs. This is the rewrite of `../report-generator/` (a Tkinter + Excel prototype).

## Stack
Python 3.12, managed with `uv`. FastAPI + Jinja2 templates + HTMX (vendored in `static/`, no CDN, because the app must work offline). SQLite through SQLModel, with migrations in Alembic. ReportLab for PDFs. Pydantic for config. pytest, ruff, pyright.

## Commands (run from this folder)
- Install: `uv sync`
- Run the app (opens the browser): `uv run report-generator`
- Dev server with reload: `uv run uvicorn report_generator.web.app:create_app --factory --reload`
- Tests: `uv run pytest` · single test: `uv run pytest tests/domain/test_scoring.py::test_name`
- Lint/format: `uv run ruff check --fix . && uv run ruff format .`
- Type check: `uv run pyright`
- Migrations: `uv run alembic revision --autogenerate -m "msg"` · `uv run alembic upgrade head`

## Layout
```
src/report_generator/
  config.py      # loads and validates config.json (Pydantic) at startup
  domain/        # pure logic: scoring, tiers, rounding. No FastAPI/SQL/ReportLab imports.
  db/            # SQLModel tables, session, repository functions
  pdf/           # ReportLab rendering + custom flowables; assets/ holds the icons
  web/           # FastAPI app, routers, templates/, static/
config/config.json   # colours, certification groups, thresholds, every text and label
tests/               # mirrors src/ (domain/, pdf/, web/)
```

## Rules
- **Layering:** `web` → `db`/`pdf` → `domain`. `domain` stays pure and is unit-tested without I/O. Routes stay thin.
- **Data model:** `Student` (name, certification) → many `MockExam` (date) → many `ExamScore` (skill, score 0–100). Exams done = number of exams. Each skill's score = mean of that skill over the 3 most recent exams by date. Never store derived values.
- **Certification groups** come from config. Startup fails if a certification appears in more than one group. The scores a form asks for come from the student's group.
- **Rounding:** round the final values once with `Decimal` ROUND_HALF_UP (not `round()`, which is banker's rounding). The rounded value is both what's displayed and what decides the tier (pass ≥ pass_threshold, average ≥ average_threshold, else fail). This logic lives only in `domain`.
- **Text:** every user-facing string (UI and PDF, Spanish) comes from config or templates, never from Python literals. Code, identifiers and commits are in English.
- **PDFs** are returned as HTTP downloads: `/students/{id}/report.pdf`, or `/reports/download?ids=…` (one reportable student gives a PDF, several give a ZIP, and students without exams are skipped). Nothing is written to disk.
- **HTMX:** routes return full pages for normal requests and partials when `HX-Request` is set. Forms are validated server-side with Pydantic, and errors are re-rendered inline.
- **Front-end:** no build step. Small vanilla scripts in `web/static/js/` (`selection.js` for checkbox state and button labels, `confirm.js` for the `<dialog>` used by `data-confirm` and `hx-confirm`, `toast.js` for notices). Pages must still work without JS; the server re-validates everything.
- **JS never contains UI text:** labels come from `data-label-*` / `data-confirm-*` attributes (`{n}` is replaced with a count). Toasts: Python sends only a notice code (`?notice=code&n=N` on redirects, `HX-Trigger: {"notice": {"code": ...}}` on HTMX responses), and the text is in `<template id="notice-texts">` in `base.html`.
- **Icons:** use the `icon(name)` macro (`_macros.html`). It reads from the vendored Lucide sprite `web/static/icons.svg`; add new icons to that sprite, never from a CDN. The logo is served from `pdf/assets` at `/assets` (one copy, shared with the PDF).
- **CSS:** `web/static/app.css` is built on design tokens (`--space-*`, `--radius-*`, surfaces). Brand and tier colours come from config through inline vars in `base.html`. Dark mode is a `prefers-color-scheme` override of the tokens only.
- **Tests:** every scoring/tier rule gets a unit test, including boundaries (e.g. 79.5 → 80 → pass). PDF tests check the output renders and includes the expected text, not pixel output. Web tests use FastAPI `TestClient` with a temporary SQLite database.
- Porting from the prototype: port the behaviour, not the code (see the root CLAUDE.md).
