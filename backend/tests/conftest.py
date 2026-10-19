from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

_test_db = Path(tempfile.gettempdir()) / "cloudpulse-pytest.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    f"sqlite+pysqlite:///{_test_db.as_posix()}",
)
os.environ["ALLOWED_ORIGINS"] = "http://testserver"
os.environ["PUBLIC_BASE_URL"] = "http://backend:8000"
os.environ["ADMIN_PASSWORD_HASH"] = PasswordHasher().hash("test-admin-password")

from app.db.models import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client

