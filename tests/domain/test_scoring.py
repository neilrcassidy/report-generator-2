from datetime import date

import pytest

from report_generator.domain.scoring import (
    ExamScores,
    Thresholds,
    Tier,
    compute_result,
    round_half_up,
    tier_for,
)

SKILLS = ["READING", "WRITING", "LISTENING"]
THRESHOLDS = Thresholds(pass_threshold=80, average_threshold=70)


def exam(day: int, reading: float, writing: float, listening: float) -> ExamScores:
    return ExamScores(
        taken_on=date(2026, 1, day),
        scores={"READING": reading, "WRITING": writing, "LISTENING": listening},
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [(79.4, 79), (79.5, 80), (80.5, 81), (0, 0), (100, 100), (64.49, 64)],
)
def test_round_half_up_always_rounds_point_five_up(value: float, expected: int) -> None:
    # Python's round(80.5) == 80 (banker's rounding); we never want that.
    assert round_half_up(value) == expected


@pytest.mark.parametrize(
    ("score", "tier"),
    [(80, Tier.PASS), (79, Tier.AVERAGE), (70, Tier.AVERAGE), (69, Tier.FAIL), (100, Tier.PASS)],
)
def test_tier_boundaries_are_inclusive(score: int, tier: Tier) -> None:
    assert tier_for(score, THRESHOLDS) is tier


def test_no_exams_gives_no_result() -> None:
    assert compute_result([], SKILLS, THRESHOLDS) is None


def test_averages_only_the_three_most_recent_exams() -> None:
    exams = [
        exam(1, 0, 0, 0),  # oldest: ignored
        exam(4, 90, 90, 90),
        exam(2, 60, 60, 60),
        exam(3, 75, 75, 75),
    ]
    result = compute_result(exams, SKILLS, THRESHOLDS)
    assert result is not None
    assert result.exams_done == 4
    assert [s.score for s in result.skills] == [75, 75, 75]  # (90 + 60 + 75) / 3
    assert result.overall == 75
    assert result.tier is Tier.AVERAGE


def test_fewer_than_three_exams_averages_what_exists() -> None:
    result = compute_result([exam(1, 80, 90, 100)], SKILLS, THRESHOLDS)
    assert result is not None
    assert [(s.skill, s.score) for s in result.skills] == [
        ("READING", 80),
        ("WRITING", 90),
        ("LISTENING", 100),
    ]
    assert result.overall == 90


def test_rounded_value_decides_the_tier() -> None:
    # Skill mean 79.5 is displayed as 80 and therefore passes (prototype showed "80 %" in yellow).
    result = compute_result([exam(1, 79, 80, 79.5), exam(2, 80, 79, 79.5)], SKILLS, THRESHOLDS)
    assert result is not None
    by_skill = {s.skill: s for s in result.skills}
    assert by_skill["READING"].score == 80
    assert by_skill["READING"].tier is Tier.PASS
    assert result.overall == 80
    assert result.tier is Tier.PASS


def test_overall_uses_unrounded_skill_means_rounded_once() -> None:
    # Skill means 69.5, 69.5, 70.6: rounded skills are 70, 70, 71 but overall mean is 69.87 -> 70.
    exams = [exam(1, 69, 69, 70.6), exam(2, 70, 70, 70.6)]
    result = compute_result(exams, SKILLS, THRESHOLDS)
    assert result is not None
    assert result.overall == 70


def test_skills_missing_from_recent_exams_are_left_out() -> None:
    exams = [ExamScores(date(2026, 1, 1), {"READING": 90})]
    result = compute_result(exams, SKILLS, THRESHOLDS)
    assert result is not None
    assert [s.skill for s in result.skills] == ["READING"]
    assert result.overall == 90
