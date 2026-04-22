"""Integration for Tuya Unsupported Sensors."""

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICES,
    CONF_REGION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import ExtraTuyaSensorsDataUpdateCoordinator
from .exceptions import (
    TuyaAuthError,
    TuyaConnectionError,
    TuyaDatacenterMismatchError,
    TuyaDiscoveryError,
    TuyaSubscriptionExpiredError,
)
from .repairs import (
    clear_runtime_issues,
    create_auth_issue,
    create_discovery_issue,
    get_discovery_probe_result,
)
from .tuya_api import TuyaAPIClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Tuya Unsupported Sensors integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


def _get_entry_value(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Get config value with options precedence."""
    if key in entry.options:
        return entry.options.get(key, default)
    return entry.data.get(key, default)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Unsupported Sensors from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    client_id = entry.data[CONF_CLIENT_ID]
    client_secret = entry.data[CONF_CLIENT_SECRET]
    region = entry.data[CONF_REGION]
    device_ids = _get_entry_value(entry, CONF_DEVICES, [])
    update_interval = _get_entry_value(entry, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    
    # Validate update_interval is within allowed range
    if update_interval < MIN_UPDATE_INTERVAL or update_interval > MAX_UPDATE_INTERVAL:
        _LOGGER.warning(
            "update_interval %d is outside valid range (%d-%d seconds), using default %d seconds",
            update_interval,
            MIN_UPDATE_INTERVAL,
            MAX_UPDATE_INTERVAL,
            DEFAULT_UPDATE_INTERVAL
        )
        update_interval = DEFAULT_UPDATE_INTERVAL
    
    api_client = TuyaAPIClient(client_id, client_secret, region)
    
    coordinator = ExtraTuyaSensorsDataUpdateCoordinator(
        hass,
        api_client,
        device_ids,
        update_interval,
        entry.entry_id,
    )
    
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        cause = err.__cause__
        if isinstance(cause, TuyaAuthError):
            create_auth_issue(hass, entry.entry_id, str(cause))
            raise ConfigEntryAuthFailed(str(cause)) from err
        if isinstance(cause, (TuyaConnectionError, TuyaDiscoveryError, TuyaDatacenterMismatchError, TuyaSubscriptionExpiredError)):
            probe_result = await get_discovery_probe_result(
                hass,
                entry.entry_id,
                client_id,
                client_secret,
                region,
            )
            create_discovery_issue(hass, entry.entry_id, str(cause), probe_result=probe_result)
            raise ConfigEntryNotReady(str(cause)) from err
        raise ConfigEntryNotReady(str(err)) from err
    
    discovered_devices = {}
    try:
        devices_list = await api_client.discover_devices()
        for device in devices_list:
            device_id = device.get("id")
            if device_id in device_ids:
                discovered_devices[device_id] = device
    except (TuyaConnectionError, TuyaDiscoveryError, TuyaDatacenterMismatchError, TuyaSubscriptionExpiredError) as err:
        _LOGGER.warning("Could not fetch device info: %s", err)
        probe_result = await get_discovery_probe_result(
            hass,
            entry.entry_id,
            client_id,
            client_secret,
            region,
        )
        create_discovery_issue(hass, entry.entry_id, str(err), probe_result=probe_result)
    except TuyaAuthError as err:
        _LOGGER.warning("Could not fetch device info: %s", err)
        create_auth_issue(hass, entry.entry_id, str(err))
    
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": api_client,
        "devices": discovered_devices,
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    await _register_devices(hass, entry, discovered_devices)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    clear_runtime_issues(hass, entry.entry_id)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle config entry updates."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry removal."""
    clear_runtime_issues(hass, entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a device from this config entry."""
    target_device_ids: set[str] = set()
    for identifier_domain, identifier_value in device_entry.identifiers:
        if identifier_domain == DOMAIN:
            raw = str(identifier_value)
            target_device_ids.add(raw)
            target_device_ids.add(raw.lower())

    if not target_device_ids:
        return False

    current_devices = list(_get_entry_value(config_entry, CONF_DEVICES, []))
    current_device_map = {str(device_id): str(device_id).lower() for device_id in current_devices}
    matching_devices = [
        original for original, lowered in current_device_map.items()
        if original in target_device_ids or lowered in target_device_ids
    ]
    if not matching_devices:
        return False

    updated_devices = [device_id for device_id in current_devices if str(device_id) not in matching_devices]
    update_interval = _get_entry_value(config_entry, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    new_data = {
        CONF_CLIENT_ID: config_entry.data[CONF_CLIENT_ID],
        CONF_CLIENT_SECRET: config_entry.data[CONF_CLIENT_SECRET],
        CONF_REGION: config_entry.data[CONF_REGION],
        CONF_DEVICES: updated_devices,
        CONF_UPDATE_INTERVAL: update_interval,
    }
    new_options = dict(config_entry.options)
    new_options[CONF_DEVICES] = updated_devices
    new_options[CONF_UPDATE_INTERVAL] = update_interval
    hass.config_entries.async_update_entry(config_entry, data=new_data, options=new_options)
    return True


async def _register_devices(
    hass: HomeAssistant, entry: ConfigEntry, discovered_devices: Dict[str, Any]
) -> None:
    """Register devices in device registry."""
    device_registry = dr.async_get(hass)
    
    for device_id, device_info in discovered_devices.items():
        # Use Tuya customName first, then name, then fallback
        device_name = device_info.get("customName") or device_info.get("name", f"Device {device_id}")
        device_model = device_info.get("product_name", "Unknown")
        
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer="Tuya",
            model=device_model,
        )
