"""Glue between stored students, config and the pure domain/pdf layers."""

from report_generator.config import AppConfig
from report_generator.db import repository as repo
from report_generator.db.models import Student
from report_generator.domain.scoring import StudentResult, Thresholds, compute_result
from report_generator.pdf.report import ReportInput


def result_for(student: Student, config: AppConfig) -> StudentResult | None:
    group = config.group_for(student.certification)
    thresholds = Thresholds(group.pass_threshold, group.average_threshold)
    return compute_result(repo.to_exam_scores(student), group.skills, thresholds)


def report_input_for(student: Student, config: AppConfig) -> ReportInput | None:
    result = result_for(student, config)
    if result is None:
        return None
    return ReportInput(student.name, student.certification, result)
