"""Integration for Tuya Unsupported Sensors."""

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICES,
    CONF_REGION,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import ExtraTuyaSensorsDataUpdateCoordinator
from .tuya_api import TuyaAPIClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Tuya Unsupported Sensors integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Unsupported Sensors from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    client_id = entry.data[CONF_CLIENT_ID]
    client_secret = entry.data[CONF_CLIENT_SECRET]
    region = entry.data[CONF_REGION]
    device_ids = entry.data[CONF_DEVICES]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, 5)
    
    api_client = TuyaAPIClient(client_id, client_secret, region)
    
    coordinator = ExtraTuyaSensorsDataUpdateCoordinator(
        hass,
        api_client,
        device_ids,
        update_interval,
    )
    
    await coordinator.async_config_entry_first_refresh()
    
    discovered_devices = {}
    try:
        devices_list = await api_client.discover_devices()
        for device in devices_list:
            device_id = device.get("id")
            if device_id in device_ids:
                discovered_devices[device_id] = device
    except Exception as err:
        _LOGGER.warning("Could not fetch device info: %s", err)
    
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": api_client,
        "devices": discovered_devices,
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    await _register_devices(hass, entry, discovered_devices)
    
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
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
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


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
