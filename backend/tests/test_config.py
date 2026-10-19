import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_https_public_base_url():
    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(environment="production", public_base_url="http://cloudpulse.example")


def test_public_base_url_is_an_approved_origin():
    settings = Settings(
        environment="test",
        public_base_url="https://cloudpulse.example/",
        allowed_origins="https://admin.example",
    )

    assert settings.origin_list == ["https://admin.example", "https://cloudpulse.example"]
