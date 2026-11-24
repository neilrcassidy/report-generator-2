from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from report_generator.settings import Settings
from report_generator.web.app import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "test.db")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as c:
        yield c
    app.state.engine.dispose()
