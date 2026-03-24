from collections.abc import Generator
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "src"))

import pytest
from fastapi.testclient import TestClient

from aces_backend.api.dependencies import get_match_repository

from aces_backend.main import app


@pytest.fixture(autouse=True)
def clear_matches() -> None:
    get_match_repository().clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
