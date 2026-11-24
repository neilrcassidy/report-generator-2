"""Student and mock exam pages."""

import json
from datetime import date
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from report_generator.config import AppConfig
from report_generator.db import repository as repo
from report_generator.db.models import Student
from report_generator.web.deps import ConfigDep, SessionDep, is_htmx, render
from report_generator.web.forms import FormErrors, parse_exam_form, parse_student_form
from report_generator.web.results import result_for
from report_generator.web.search import filter_students

router = APIRouter(prefix="/students")


def _load(session: SessionDep, student_id: int) -> Student:
    student = repo.get_student(session, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return student


def _exam_context(
    student: Student,
    config: AppConfig,
    errors: FormErrors | None = None,
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "student": student,
        "skills": config.group_for(student.certification).skills,
        "exams": repo.exams_newest_first(student),
        "result": result_for(student, config),
        "errors": errors or {},
        "values": values or {"taken_on": date.today().isoformat()},
    }


def _redirect(url: str, notice: str | None = None, **params: object) -> RedirectResponse:
    """303 redirect, optionally carrying a notice code for the toast (text lives in templates)."""
    if notice:
        url += "?" + urlencode({"notice": notice, **params})
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def _with_notice(response: Response, notice: str) -> Response:
    """Tell htmx (via HX-Trigger) to show a toast for this notice code."""
    response.headers["HX-Trigger"] = json.dumps({"notice": {"code": notice}})
    return response


@router.get("", response_class=HTMLResponse)
def list_students(
    request: Request,
    session: SessionDep,
    config: ConfigDep,
    q: str = "",
    cert: str = "",
) -> HTMLResponse:
    all_students = repo.list_students(session)
    students = filter_students(all_students, q, cert)
    context = {
        "rows": [(s, result_for(s, config)) for s in students],
        "has_students": bool(all_students),
        "q": q,
        "cert": cert,
    }
    template = "students/_rows.html" if is_htmx(request) else "students/list.html"
    return render(request, template, context)


@router.post("/delete")
def delete_students(
    session: SessionDep, ids: Annotated[list[int] | None, Form()] = None
) -> RedirectResponse:
    deleted = repo.delete_students(session, ids or [])
    return _redirect("/students", "students_deleted", n=deleted)


@router.get("/new", response_class=HTMLResponse)
def new_student(request: Request) -> HTMLResponse:
    return render(request, "students/new.html", {"errors": {}, "values": {}})


@router.post("", response_model=None)
async def create_student(request: Request, session: SessionDep, config: ConfigDep) -> Response:
    data = dict(await request.form())
    form, errors = parse_student_form(data, config.certifications)
    if form is None:
        return render(
            request,
            "students/new.html",
            {"errors": errors, "values": data},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    student = repo.create_student(session, form.name, form.certification)
    return _redirect(f"/students/{student.id}", "student_created")


@router.get("/{student_id}", response_class=HTMLResponse)
def show_student(
    request: Request, student_id: int, session: SessionDep, config: ConfigDep
) -> HTMLResponse:
    student = _load(session, student_id)
    return render(request, "students/detail.html", _exam_context(student, config))


@router.post("/{student_id}/delete")
def delete_student(student_id: int, session: SessionDep) -> RedirectResponse:
    repo.delete_student(session, _load(session, student_id))
    return _redirect("/students", "student_deleted")


def _exams_response(
    request: Request,
    student: Student,
    config: AppConfig,
    errors: FormErrors | None = None,
    values: dict[str, Any] | None = None,
    notice: str | None = None,
) -> Response:
    """HTMX gets the exams partial back (always 200 so htmx swaps it in);
    plain form posts get a redirect, or the full page with errors."""
    context = _exam_context(student, config, errors, values)
    if is_htmx(request):
        response = render(request, "students/_exams.html", context)
        return _with_notice(response, notice) if notice else response
    if errors:
        return render(
            request, "students/detail.html", context, status.HTTP_422_UNPROCESSABLE_CONTENT
        )
    return _redirect(f"/students/{student.id}", notice)


@router.post("/{student_id}/exams", response_model=None)
async def add_exam(
    request: Request, student_id: int, session: SessionDep, config: ConfigDep
) -> Response:
    student = _load(session, student_id)
    data = dict(await request.form())
    skills = config.group_for(student.certification).skills
    form, errors = parse_exam_form(data, skills)
    if form is None:
        return _exams_response(request, student, config, errors, data)
    repo.add_exam(session, student, form.taken_on, form.scores)
    session.refresh(student)
    return _exams_response(request, student, config, notice="exam_added")


@router.post("/{student_id}/exams/{exam_id}/delete", response_model=None)
def delete_exam(
    request: Request, student_id: int, exam_id: int, session: SessionDep, config: ConfigDep
) -> Response:
    student = _load(session, student_id)
    if not repo.delete_exam(session, student, exam_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    session.refresh(student)
    return _exams_response(request, student, config, notice="exam_deleted")
