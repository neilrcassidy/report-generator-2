"""Server-side validation of submitted forms.

Errors are returned as {field_name: error_code}. Templates turn codes into
(Spanish) messages, so no user-facing text lives in Python.
"""

from collections.abc import Callable, Mapping, Sequence
from datetime import date
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints, ValidationError

FormErrors = dict[str, str]
Loc = tuple[int | str, ...]

_ERROR_CODES = {
    "missing": "required",
    "string_too_short": "required",
    "string_too_long": "too_long",
    "greater_than_equal": "out_of_range",
    "less_than_equal": "out_of_range",
}


class StudentForm(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    certification: str


class ExamForm(BaseModel):
    taken_on: date
    scores: dict[str, Annotated[float, Field(ge=0, le=100)]]


def score_field(skill: str) -> str:
    return f"score:{skill}"


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _top_field(loc: Loc) -> str:
    return str(loc[0]) if loc else ""


def _collect(exc: ValidationError, field_for_loc: Callable[[Loc], str]) -> FormErrors:
    errors: FormErrors = {}
    for err in exc.errors():
        field = field_for_loc(err["loc"])
        errors.setdefault(field, _ERROR_CODES.get(err["type"], "invalid"))
    return errors


def parse_student_form(
    data: Mapping[str, Any], certifications: Sequence[str]
) -> tuple[StudentForm | None, FormErrors]:
    errors: FormErrors = {}
    try:
        form = StudentForm.model_validate(
            {"name": data.get("name", ""), "certification": data.get("certification", "")}
        )
    except ValidationError as exc:
        return None, _collect(exc, _top_field)
    if form.certification not in certifications:
        errors["certification"] = "required" if not form.certification else "invalid"
        return None, errors
    return form, errors


def parse_exam_form(
    data: Mapping[str, Any], skills: Sequence[str]
) -> tuple[ExamForm | None, FormErrors]:
    errors: FormErrors = {}
    raw_date = data.get("taken_on")
    if _blank(raw_date):
        errors["taken_on"] = "required"
    raw_scores: dict[str, Any] = {}
    for skill in skills:
        value = data.get(score_field(skill))
        if _blank(value):
            errors[score_field(skill)] = "required"
        else:
            raw_scores[skill] = value
    if errors:
        return None, errors

    def field_for(loc: Loc) -> str:
        if len(loc) >= 2 and loc[0] == "scores":
            return score_field(str(loc[1]))
        return _top_field(loc)

    try:
        return ExamForm.model_validate({"taken_on": raw_date, "scores": raw_scores}), {}
    except ValidationError as exc:
        return None, _collect(exc, field_for)
