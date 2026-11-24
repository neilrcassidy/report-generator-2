"""SQLModel tables. Only raw entered data is stored; averages are always computed.

(No `from __future__ import annotations` here: SQLModel relationships need real types.)
"""

from datetime import UTC, date, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def _now() -> datetime:
    return datetime.now(UTC)


class Student(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    certification: str
    created_at: datetime = Field(default_factory=_now)

    exams: list["MockExam"] = Relationship(back_populates="student", cascade_delete=True)


class MockExam(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", ondelete="CASCADE", index=True)
    taken_on: date
    created_at: datetime = Field(default_factory=_now)

    student: Student = Relationship(back_populates="exams")
    scores: list["ExamScore"] = Relationship(back_populates="exam", cascade_delete=True)


class ExamScore(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("exam_id", "skill"),)

    id: int | None = Field(default=None, primary_key=True)
    exam_id: int = Field(foreign_key="mockexam.id", ondelete="CASCADE", index=True)
    skill: str
    score: float = Field(ge=0, le=100)

    exam: MockExam = Relationship(back_populates="scores")
