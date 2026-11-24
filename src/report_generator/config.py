"""Loading and validation of config/config.json."""

import json
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Threshold = Annotated[int, Field(ge=0, le=100)]
HexColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Colors(_Model):
    green_dark: HexColor
    green_light: HexColor
    yellow: HexColor
    red: HexColor
    black: HexColor


class CertificationGroup(_Model):
    certifications: Annotated[list[str], Field(min_length=1)]
    skills: Annotated[list[str], Field(min_length=1)]
    pass_threshold: Threshold
    average_threshold: Threshold

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.average_threshold > self.pass_threshold:
            raise ValueError("average_threshold must not be greater than pass_threshold")
        if len(set(self.skills)) != len(self.skills):
            raise ValueError(f"duplicate skills in group {self.certifications}")
        return self


class Labels(_Model):
    student: str
    certification: str
    exams_done: str
    individual_score: str
    total_score: str
    status: str


class Texts(_Model):
    title: str
    subtitle: str
    intro_text: str
    pass_conclusion_text: str
    average_conclusion_text: str
    fail_conclusion_text: str
    doubt_text: str = ""
    status_pass: str
    status_average: str
    status_fail: str
    labels: Labels


class Phone(_Model):
    landline: str | None = None
    mobile: str | None = None


class Contacts(_Model):
    phone: Phone
    email: str
    website: str


class AppConfig(_Model):
    colors: Colors
    certification_groups: Annotated[
        list[CertificationGroup], Field(alias="certification_skills_sets", min_length=1)
    ]
    texts: Texts
    contacts: Contacts

    @model_validator(mode="after")
    def _unique_certifications(self) -> Self:
        # A certification in two groups would make its skills/thresholds ambiguous.
        seen: set[str] = set()
        duplicates: set[str] = set()
        for group in self.certification_groups:
            for cert in group.certifications:
                (duplicates if cert in seen else seen).add(cert)
        if duplicates:
            raise ValueError(
                "certifications listed in more than one group: " + ", ".join(sorted(duplicates))
            )
        return self

    @property
    def certifications(self) -> list[str]:
        return [c for group in self.certification_groups for c in group.certifications]

    def group_for(self, certification: str) -> CertificationGroup:
        for group in self.certification_groups:
            if certification in group.certifications:
                return group
        raise KeyError(f"unknown certification: {certification}")


def load_config(path: Path) -> AppConfig:
    with path.open(encoding="utf-8") as f:
        return AppConfig.model_validate(json.load(f))
