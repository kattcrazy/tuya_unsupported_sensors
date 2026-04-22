"""Diagnostics support for Tuya Unsupported Sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, DOMAIN

TO_REDACT = {
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    "access_token",
    "token",
    "sign",
    "Authorization",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {})
    coordinator = runtime.get("coordinator")
    client = runtime.get("client")

    diagnostics = {
        "entry": {
            "entry_id": config_entry.entry_id,
            "data": dict(config_entry.data),
            "options": dict(config_entry.options),
        },
        "runtime": {
            "device_count": len(runtime.get("devices", {})),
            "known_device_ids": list(runtime.get("devices", {}).keys()),
            "coordinator_last_update_success": getattr(coordinator, "last_update_success", None),
            "coordinator_last_exception": repr(getattr(coordinator, "last_exception", None)),
            "token_expires_at": str(getattr(client, "_token_expires_at", None)),
        },
    }
    return async_redact_data(diagnostics, TO_REDACT)
