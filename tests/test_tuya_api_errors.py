"""Tests for typed Tuya API error classification."""

from custom_components.tuya_unsupported_sensors.exceptions import (
    TuyaAuthError,
    TuyaDatacenterMismatchError,
    TuyaDiscoveryError,
    TuyaSubscriptionExpiredError,
)
from custom_components.tuya_unsupported_sensors.tuya_api import TuyaAPIClient


def test_classify_discovery_error_subscription() -> None:
    """Subscription/permission failures map to subscription exception."""
    error = TuyaAPIClient._classify_discovery_error(
        "No permissions. Your subscription to cloud development plan has expired",
        28841005,
    )
    assert isinstance(error, TuyaSubscriptionExpiredError)


def test_classify_discovery_error_datacenter() -> None:
    """Datacenter wording maps to datacenter mismatch exception."""
    error = TuyaAPIClient._classify_discovery_error(
        "Region mismatch for this cloud project datacenter",
        1106,
    )
    assert isinstance(error, TuyaDatacenterMismatchError)


def test_classify_discovery_error_auth() -> None:
    """Token/auth failures map to auth exception."""
    error = TuyaAPIClient._classify_discovery_error("token invalid", 1010)
    assert isinstance(error, TuyaAuthError)


def test_classify_discovery_error_fallback() -> None:
    """Unknown discovery errors map to generic discovery exception."""
    error = TuyaAPIClient._classify_discovery_error("unexpected discovery failure", "unknown")
    assert isinstance(error, TuyaDiscoveryError)
