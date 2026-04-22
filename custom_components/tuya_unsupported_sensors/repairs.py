"""Repairs issue helpers for Tuya Unsupported Sensors."""

from __future__ import annotations

from time import monotonic
from typing import Any

from homeassistant.helpers import issue_registry as ir

from .const import (
    DISCOVERY_HELP_URL,
    DOMAIN,
    IOT_CORE_URL,
    ISSUE_ID_API_AUTH_FAILED,
    ISSUE_ID_DISCOVERY_FAILED,
)

PROBE_CACHE_KEY = "_discovery_probe_cache"
PROBE_CACHE_TTL_SECONDS = 1800


def _issue_id(base_id: str, entry_id: str) -> str:
    """Build a unique issue ID per config entry."""
    return f"{base_id}_{entry_id}"


def create_auth_issue(hass, entry_id: str, error: str = "") -> None:
    """Create/update auth failure issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(ISSUE_ID_API_AUTH_FAILED, entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_ID_API_AUTH_FAILED,
        translation_placeholders={
            "error": error or "Unknown authentication error",
        },
    )


async def get_discovery_probe_result(
    hass,
    entry_id: str,
    client_id: str,
    client_secret: str,
    current_region: str,
) -> str:
    """Run or reuse a cached datacenter probe and return guidance text."""
    from .tuya_api import probe_datacenters

    domain_data = hass.data.setdefault(DOMAIN, {})
    cache: dict[str, dict[str, Any]] = domain_data.setdefault(PROBE_CACHE_KEY, {})
    cache_entry = cache.get(entry_id)
    now = monotonic()
    if (
        cache_entry
        and cache_entry.get("client_id") == client_id
        and cache_entry.get("current_region") == current_region
        and now - cache_entry.get("timestamp", 0) < PROBE_CACHE_TTL_SECONDS
    ):
        return cache_entry.get("guidance", "Probe could not determine a likely cause.")

    probe = await probe_datacenters(client_id, client_secret)
    successful_regions = probe.get("successful_regions", [])
    subscription_regions = probe.get("subscription_expired_regions", [])
    auth_regions = probe.get("auth_error_regions", [])

    if successful_regions:
        preferred_region = successful_regions[0]
        if current_region in successful_regions:
            guidance = (
                f"Automatic datacenter probe found working region(s): {', '.join(successful_regions)}. "
                f"Current region '{current_region}' appears valid."
            )
        else:
            guidance = (
                f"Automatic datacenter probe found working region(s): {', '.join(successful_regions)}. "
                f"Update integration region to '{preferred_region}'."
            )
    elif subscription_regions:
        guidance = (
            "Automatic datacenter probe did not find a working region and returned subscription/permission "
            f"errors in: {', '.join(subscription_regions)}. This strongly suggests IoT Core subscription expiry."
        )
    elif auth_regions and len(auth_regions) == len(probe.get("results", [])):
        guidance = (
            "Automatic datacenter probe received authentication errors in all regions. "
            "Verify Client ID and Client Secret."
        )
    else:
        guidance = (
            "Automatic datacenter probe could not determine a single cause. "
            "Check region, credentials, subscription state, and connectivity."
        )

    cache[entry_id] = {
        "timestamp": now,
        "client_id": client_id,
        "current_region": current_region,
        "guidance": guidance,
    }
    return guidance


def create_discovery_issue(hass, entry_id: str, error: str = "", probe_result: str = "") -> None:
    """Create/update discovery/datacenter/subscription issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(ISSUE_ID_DISCOVERY_FAILED, entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_ID_DISCOVERY_FAILED,
        learn_more_url=DISCOVERY_HELP_URL,
        translation_placeholders={
            "error": error or "Unknown discovery error",
            "iot_core_url": IOT_CORE_URL,
            "probe_result": probe_result or "Automatic probe unavailable.",
        },
    )


def clear_runtime_issues(hass, entry_id: str) -> None:
    """Clear known runtime issues for an entry."""
    ir.async_delete_issue(hass, DOMAIN, _issue_id(ISSUE_ID_API_AUTH_FAILED, entry_id))
    ir.async_delete_issue(hass, DOMAIN, _issue_id(ISSUE_ID_DISCOVERY_FAILED, entry_id))
    cache: dict[str, dict[str, Any]] | None = hass.data.get(DOMAIN, {}).get(PROBE_CACHE_KEY)
    if cache and entry_id in cache:
        del cache[entry_id]
