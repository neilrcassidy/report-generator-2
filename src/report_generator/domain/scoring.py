"""Pure scoring rules: last-N averages, rounding and result tiers.

Rounding happens exactly once, here. The rounded value is what gets displayed
and also what decides the tier, so a report never shows "80 %" next to a fail.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

EXAMS_AVERAGED = 3


class Tier(StrEnum):
    PASS = "pass"
    AVERAGE = "average"
    FAIL = "fail"


@dataclass(frozen=True)
class Thresholds:
    pass_threshold: int
    average_threshold: int


@dataclass(frozen=True)
class ExamScores:
    taken_on: date
    scores: Mapping[str, float]


@dataclass(frozen=True)
class SkillResult:
    skill: str
    score: int
    tier: Tier


@dataclass(frozen=True)
class StudentResult:
    exams_done: int
    skills: list[SkillResult]
    overall: int
    tier: Tier


def round_half_up(value: float | Decimal) -> int:
    """Round to a whole percentage, .5 always up (Python's round() is banker's rounding)."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def tier_for(score: int, thresholds: Thresholds) -> Tier:
    if score >= thresholds.pass_threshold:
        return Tier.PASS
    if score >= thresholds.average_threshold:
        return Tier.AVERAGE
    return Tier.FAIL


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def compute_result(
    exams: Sequence[ExamScores],
    skills: Sequence[str],
    thresholds: Thresholds,
) -> StudentResult | None:
    """Score a student from their exams, or None if they have no exams yet.

    Each skill is averaged over the most recent EXAMS_AVERAGED exams that include it.
    The overall score is the mean of the unrounded skill averages, rounded once.
    Skills with no scores in those exams are left out.
    """
    if not exams:
        return None

    recent = sorted(exams, key=lambda e: e.taken_on, reverse=True)[:EXAMS_AVERAGED]

    skill_means: dict[str, Decimal] = {}
    for skill in skills:
        values = [Decimal(str(e.scores[skill])) for e in recent if skill in e.scores]
        if values:
            skill_means[skill] = _mean(values)

    if not skill_means:
        return None

    skill_results: list[SkillResult] = []
    for skill, mean in skill_means.items():
        score = round_half_up(mean)
        skill_results.append(SkillResult(skill, score, tier_for(score, thresholds)))
    overall = round_half_up(_mean(list(skill_means.values())))
    return StudentResult(
        exams_done=len(exams),
        skills=skill_results,
        overall=overall,
        tier=tier_for(overall, thresholds),
    )
