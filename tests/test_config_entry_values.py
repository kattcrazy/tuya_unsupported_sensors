"""Tests for config/option value precedence helpers."""

from types import SimpleNamespace

from custom_components.tuya_unsupported_sensors.__init__ import _get_entry_value as get_entry_runtime
from custom_components.tuya_unsupported_sensors.config_flow import _get_entry_value as get_entry_flow


def test_get_entry_value_prefers_options() -> None:
    """Options should override data when key exists in options."""
    entry = SimpleNamespace(data={"devices": ["a"]}, options={"devices": ["b"]})
    assert get_entry_runtime(entry, "devices", []) == ["b"]
    assert get_entry_flow(entry, "devices", []) == ["b"]


def test_get_entry_value_falls_back_to_data() -> None:
    """Data should be returned when options do not contain the key."""
    entry = SimpleNamespace(data={"update_interval": 120}, options={})
    assert get_entry_runtime(entry, "update_interval", 60) == 120
    assert get_entry_flow(entry, "update_interval", 60) == 120


def test_get_entry_value_default_when_missing() -> None:
    """Default should be returned if key is missing in both."""
    entry = SimpleNamespace(data={}, options={})
    assert get_entry_runtime(entry, "missing", "x") == "x"
    assert get_entry_flow(entry, "missing", "x") == "x"
