"""PDF downloads: one student's report, or the reports of a selection of students."""

from datetime import date
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from report_generator.db import repository as repo
from report_generator.pdf.report import render_report, render_zip, report_filename
from report_generator.web.deps import ConfigDep, SessionDep
from report_generator.web.results import report_input_for

router = APIRouter()


def _attachment(content: bytes, media_type: str, filename: str) -> Response:
    # filename= is an ASCII fallback; filename*= carries the real (UTF-8) name, e.g. "López".
    ascii_name = filename.encode("ascii", "replace").decode().replace("?", "_").replace('"', "")
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"
    return Response(content, media_type=media_type, headers={"Content-Disposition": disposition})


@router.get("/students/{student_id}/report.pdf")
def student_report(student_id: int, session: SessionDep, config: ConfigDep) -> Response:
    student = repo.get_student(session, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    report = report_input_for(student, config)
    if report is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Student has no exams yet")
    pdf = render_report(report, config)
    return _attachment(pdf, "application/pdf", report_filename(student.name))


@router.get("/reports/download")
def download_reports(
    session: SessionDep, config: ConfigDep, ids: Annotated[list[int] | None, Query()] = None
) -> Response:
    """The selected students' reports: one PDF for a single student, otherwise a ZIP.
    Students without exams (and unknown ids) are skipped."""
    students = repo.get_students(session, ids or [])
    reports = [r for s in students if (r := report_input_for(s, config)) is not None]
    if not reports:
        raise HTTPException(status.HTTP_409_CONFLICT, "None of the selected students has exams")
    if len(reports) == 1:
        report = reports[0]
        pdf = render_report(report, config)
        return _attachment(pdf, "application/pdf", report_filename(report.student_name))
    archive = render_zip(reports, config)
    return _attachment(archive, "application/zip", f"informes_{date.today().isoformat()}.zip")
