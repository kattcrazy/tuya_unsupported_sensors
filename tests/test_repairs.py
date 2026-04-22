"""Tests for repairs issue ID helper."""

from custom_components.tuya_unsupported_sensors.repairs import _issue_id


def test_issue_id_is_namespaced_per_entry() -> None:
    """Issue IDs should be unique per entry ID."""
    assert _issue_id("api_auth_failed", "abc123") == "api_auth_failed_abc123"
