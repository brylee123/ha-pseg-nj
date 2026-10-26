"""Native Home Assistant tests: run in a matching Linux HA test environment."""

import pytest


@pytest.fixture(autouse=True)
def custom_integration(enable_custom_integrations):
    """Enable this custom integration for native HA tests."""
    return None


@pytest.fixture(autouse=True)
def recorder_for_tests(recorder_mock):
    """Initialize Recorder through HA's native fixture before dependencies load."""
    return recorder_mock


@pytest.fixture
def mock_recorder_before_hass(recorder_db_url):
    """Resolve the database configuration before Home Assistant starts."""
    return None
