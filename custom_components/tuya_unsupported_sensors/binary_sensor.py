"""Binary sensor platform for Tuya Unsupported Sensors integration."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    BINARY_SENSOR_PROPERTY_CODES,
    BINARY_SENSOR_VALUE_MAP,
    CONF_DEVICES,
    DOMAIN,
)
from .coordinator import ExtraTuyaSensorsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _is_binary_value(value: Any) -> bool:
    """Check if value should be treated as binary sensor."""
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return value in (0, 1)
    if isinstance(value, str):
        value_lower = value.lower()
        for state_values in BINARY_SENSOR_VALUE_MAP.values():
            if value_lower in state_values:
                return True
    return False


def _is_likely_contact_sensor(property_code: str, value: Any) -> bool:
    """Check if property code and value suggest a contact sensor.
    
    This is a heuristic to catch contact sensors that use non-standard property codes.
    """
    property_code_lower = property_code.lower()
    
    # Check if property code contains contact/door/sensor keywords
    contact_keywords = ["door", "contact", "sensor", "switch"]
    has_contact_keyword = any(keyword in property_code_lower for keyword in contact_keywords)
    
    if not has_contact_keyword:
        return False
    
    # Check if value is binary-like
    return _is_binary_value(value)


def _normalize_binary_value(value: Any) -> bool:
    """Normalize binary sensor value to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in BINARY_SENSOR_VALUE_MAP["on"]:
            return True
        if value_lower in BINARY_SENSOR_VALUE_MAP["off"]:
            return False
    
    return bool(value)


def _get_binary_sensor_device_class(property_code: str) -> Optional[str]:
    """Get device class for binary sensor based on property code."""
    for device_class, codes in BINARY_SENSOR_PROPERTY_CODES.items():
        if property_code.lower() in codes:
            if device_class == "contact":
                return BinarySensorDeviceClass.DOOR
            if device_class == "motion":
                return BinarySensorDeviceClass.MOTION
            if device_class == "occupancy":
                return BinarySensorDeviceClass.OCCUPANCY
            if device_class == "online":
                return BinarySensorDeviceClass.CONNECTIVITY
    return None


def _get_friendly_name(property_code: str) -> str:
    """Get friendly name for property code."""
    name_mapping = {
        "doorcontact_state": "Contact",
        "door_sensor_state": "Contact",
        "contact": "Contact",
        "pir": "Motion",
        "pir_state": "Motion",
        "motion": "Motion",
        "presence_state": "Occupancy",
        "presence": "Occupancy",
        "online": "Online",
        "automatic_lock": "Auto Lock",
        "rtc_lock": "RTC Lock Status",
    }
    
    # Check exact match first
    if property_code in name_mapping:
        return name_mapping[property_code]
    
    # Check lowercase match
    property_code_lower = property_code.lower()
    if property_code_lower in name_mapping:
        return name_mapping[property_code_lower]
    
    # Default: convert property code to title case
    return property_code.replace("_", " ").title()


def _resolve_binary_unique_id(
    entity_registry,
    device_registry,
    config_entry_id: str,
    device_id: str,
    device_name: str,
    property_code: str,
) -> str:
    """Resolve unique_id with backward compatibility for upgraded users."""
    device_entry = device_registry.async_get_device(identifiers={(DOMAIN, device_id)})
    if device_entry is not None:
        existing_entries = er.async_entries_for_device(
            entity_registry, device_entry.id, include_disabled_entities=True
        )
        friendly_suffix = f"_{slugify(_get_friendly_name(property_code))}"
        property_suffix = f"_{slugify(property_code)}"
        matching_entries = [
            entry
            for entry in existing_entries
            if entry.config_entry_id == config_entry_id
            and entry.entity_id.startswith("binary_sensor.")
            and (
                entry.unique_id.endswith(friendly_suffix)
                or entry.unique_id.endswith(property_suffix)
            )
        ]
        if matching_entries:
            active_matches = [entry for entry in matching_entries if entry.disabled_by is None]
            selected = (active_matches or matching_entries)[0]
            return selected.unique_id

    friendly_name = _get_friendly_name(property_code)
    legacy_unique_id = f"{slugify(device_name)}_{slugify(friendly_name)}"
    stable_unique_id = f"{slugify(device_id)}_{slugify(property_code)}"

    if er.async_get_entity_id("binary_sensor", DOMAIN, legacy_unique_id):
        return legacy_unique_id
    if er.async_get_entity_id("binary_sensor", DOMAIN, stable_unique_id):
        return stable_unique_id
    return stable_unique_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya Unsupported Sensors binary sensor entities."""
    coordinator: ExtraTuyaSensorsDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]["coordinator"]
    device_ids = entry.data[CONF_DEVICES]
    discovered_devices = hass.data[DOMAIN][entry.entry_id].get("devices", {})
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    
    entities = []
    
    binary_codes = set()
    for codes in BINARY_SENSOR_PROPERTY_CODES.values():
        binary_codes.update(codes)
    
    for device_id in device_ids:
        device_info = discovered_devices.get(device_id, {})
        # Use Tuya customName first, then name, then fallback
        device_name = device_info.get("customName") or device_info.get("name", f"Device {device_id}")
        device_model = device_info.get("product_name", "Unknown")
        
        device_data = coordinator.data.get(device_id, {})
        
        if not device_data:
            _LOGGER.warning(
                "No data available for device %s (%s). Device may be offline or have no properties.",
                device_id,
                device_name
            )
            continue
        
        _LOGGER.debug(
            "Processing device %s (%s) with properties: %s",
            device_id,
            device_name,
            list(device_data.keys())
        )
        
        for property_code, value in device_data.items():
            property_code_lower = property_code.lower()
            
            # Skip non-sensor properties
            if property_code_lower in ("temp_unit_convert",):
                continue
            
            # Prioritize known binary sensor property codes
            if property_code_lower in binary_codes:
                unique_id = _resolve_binary_unique_id(
                    entity_registry, device_registry, entry.entry_id, device_id, device_name, property_code
                )
                entity = ExtraTuyaBinarySensor(
                    coordinator=coordinator,
                    device_id=device_id,
                    device_name=device_name,
                    device_model=device_model,
                    property_code=property_code,
                    unique_id=unique_id,
                )
                entities.append(entity)
            elif _is_binary_value(value):
                # Also create binary sensors for other binary values
                unique_id = _resolve_binary_unique_id(
                    entity_registry, device_registry, entry.entry_id, device_id, device_name, property_code
                )
                entity = ExtraTuyaBinarySensor(
                    coordinator=coordinator,
                    device_id=device_id,
                    device_name=device_name,
                    device_model=device_model,
                    property_code=property_code,
                    unique_id=unique_id,
                )
                entities.append(entity)
            elif _is_likely_contact_sensor(property_code, value):
                # Heuristic: property codes containing contact/door keywords with binary-like values
                _LOGGER.debug(
                    "Detected likely contact sensor: %s.%s = %s",
                    device_id,
                    property_code,
                    value
                )
                unique_id = _resolve_binary_unique_id(
                    entity_registry, device_registry, entry.entry_id, device_id, device_name, property_code
                )
                entity = ExtraTuyaBinarySensor(
                    coordinator=coordinator,
                    device_id=device_id,
                    device_name=device_name,
                    device_model=device_model,
                    property_code=property_code,
                    unique_id=unique_id,
                )
                entities.append(entity)
    
    if not entities:
        _LOGGER.warning(
            "No binary sensor entities created for devices: %s. "
            "This may indicate devices have no binary properties or use unrecognized property codes.",
            device_ids
        )
    
    _LOGGER.info("Created %d binary sensor entities", len(entities))
    async_add_entities(entities)


class ExtraTuyaBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Tuya binary sensor."""

    def __init__(
        self,
        coordinator: ExtraTuyaSensorsDataUpdateCoordinator,
        device_id: str,
        device_name: str,
        device_model: str,
        property_code: str,
        unique_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._device_model = device_model
        self._property_code = property_code
        
        friendly_name = _get_friendly_name(property_code)
        self._attr_name = f"{device_name} {friendly_name}"
        
        self._attr_unique_id = unique_id
        
        device_class = _get_binary_sensor_device_class(property_code)
        if device_class:
            self._attr_device_class = device_class

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Tuya",
            model=self._device_model,
        )

    @property
    def is_on(self) -> Optional[bool]:
        """Return the state of the binary sensor."""
        device_data = self.coordinator.data.get(self._device_id, {})
        value = device_data.get(self._property_code)
        
        if value is None:
            return None
        
        return _normalize_binary_value(value)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        device_data = self.coordinator.data.get(self._device_id, {})
        raw_value = device_data.get(self._property_code)
        
        return {
            "device_id": self._device_id,
            "property_code": self._property_code,
            "raw_value": raw_value,
        }
