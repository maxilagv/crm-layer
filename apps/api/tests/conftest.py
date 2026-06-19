import uuid

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def organization_id() -> uuid.UUID:
    return uuid.uuid4()
