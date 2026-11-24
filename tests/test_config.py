import copy
import json
from typing import Any

import pytest
from pydantic import ValidationError

from report_generator.config import AppConfig, load_config
from report_generator.settings import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"


@pytest.fixture
def raw_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_shipped_config_is_valid() -> None:
    config = load_config(CONFIG_PATH)
    assert config.certifications == ["A1", "A2", "B1", "B2", "C1"]
    assert config.group_for("B2").skills == ["READING", "USE OF ENGLISH", "WRITING", "LISTENING"]
    assert config.group_for("A1").pass_threshold == 80


def test_certification_in_two_groups_is_rejected(raw_config: dict[str, Any]) -> None:
    raw = copy.deepcopy(raw_config)
    raw["certification_skills_sets"][1]["certifications"].append("B1")
    with pytest.raises(ValidationError, match="more than one group: B1"):
        AppConfig.model_validate(raw)


def test_average_threshold_above_pass_is_rejected(raw_config: dict[str, Any]) -> None:
    raw = copy.deepcopy(raw_config)
    raw["certification_skills_sets"][0]["average_threshold"] = 90
    with pytest.raises(ValidationError, match="average_threshold"):
        AppConfig.model_validate(raw)


def test_missing_label_is_rejected(raw_config: dict[str, Any]) -> None:
    raw = copy.deepcopy(raw_config)
    del raw["texts"]["labels"]["status"]
    with pytest.raises(ValidationError):
        AppConfig.model_validate(raw)


def test_unknown_certification_lookup_raises() -> None:
    with pytest.raises(KeyError):
        load_config(CONFIG_PATH).group_for("Z9")
