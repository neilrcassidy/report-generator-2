"""Database access functions used by the web layer."""

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any, cast

from sqlalchemy.orm import QueryableAttribute, selectinload
from sqlmodel import Session, col, select

from report_generator.db.models import ExamScore, MockExam, Student
from report_generator.domain.scoring import ExamScores


def _rel(attr: object) -> QueryableAttribute[Any]:
    """SQLModel types relationships as plain lists; SQLAlchemy loaders need the attribute."""
    return cast(QueryableAttribute[Any], attr)


def _students_query():
    return select(Student).options(
        selectinload(_rel(Student.exams)).selectinload(_rel(MockExam.scores))
    )


def list_students(session: Session) -> Sequence[Student]:
    return session.exec(_students_query().order_by(col(Student.name))).all()


def get_students(session: Session, ids: Iterable[int]) -> Sequence[Student]:
    """Students with the given ids (unknown ids are ignored), ordered by name."""
    stmt = _students_query().where(col(Student.id).in_(set(ids))).order_by(col(Student.name))
    return session.exec(stmt).all()


def delete_students(session: Session, ids: Iterable[int]) -> int:
    students = get_students(session, ids)
    for student in students:
        session.delete(student)
    session.commit()
    return len(students)


def get_student(session: Session, student_id: int) -> Student | None:
    return session.exec(_students_query().where(Student.id == student_id)).first()


def create_student(session: Session, name: str, certification: str) -> Student:
    student = Student(name=name, certification=certification)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def delete_student(session: Session, student: Student) -> None:
    session.delete(student)
    session.commit()


def add_exam(
    session: Session, student: Student, taken_on: date, scores: Mapping[str, float]
) -> MockExam:
    assert student.id is not None
    exam = MockExam(student_id=student.id, taken_on=taken_on)
    session.add(exam)
    session.flush()
    assert exam.id is not None
    session.add_all(
        ExamScore(exam_id=exam.id, skill=skill, score=score) for skill, score in scores.items()
    )
    session.commit()
    session.refresh(exam)
    return exam


def delete_exam(session: Session, student: Student, exam_id: int) -> bool:
    exam = session.get(MockExam, exam_id)
    if exam is None or exam.student_id != student.id:
        return False
    session.delete(exam)
    session.commit()
    return True


def exams_newest_first(student: Student) -> list[MockExam]:
    return sorted(student.exams, key=lambda e: (e.taken_on, e.id or 0), reverse=True)


def to_exam_scores(student: Student) -> list[ExamScores]:
    return [
        ExamScores(taken_on=e.taken_on, scores={s.skill: s.score for s in e.scores})
        # Newest first with a stable id tie-break, so same-day exams average deterministically.
        for e in exams_newest_first(student)
    ]
