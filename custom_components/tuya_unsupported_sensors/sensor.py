"""Sensor platform for Tuya Unsupported Sensors integration."""

import logging
from typing import Any, Dict, Optional, Union

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    CONF_DEVICES,
    DOMAIN,
    SENSOR_PROPERTY_CODES,
)
from .coordinator import ExtraTuyaSensorsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _is_numeric_value(value: Any) -> bool:
    """Check if value is numeric."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _get_friendly_name(property_code: str) -> str:
    """Get friendly name for property code."""
    name_mapping = {
        "battery_state": "Battery",
        "humidity_value": "Humidity",
        "temp_current": "Temperature",
        "doorcontact_state": "Contact",
        "temp": "Temperature",
        "temperature": "Temperature",
        "humidity": "Humidity",
        "battery": "Battery",
        "battery_percentage": "Battery",
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


def _get_sensor_device_class(property_code: str) -> Optional[str]:
    """Get device class for sensor based on property code."""
    for device_class, codes in SENSOR_PROPERTY_CODES.items():
        if property_code.lower() in codes:
            if device_class == "temperature":
                return SensorDeviceClass.TEMPERATURE
            if device_class == "humidity":
                return SensorDeviceClass.HUMIDITY
            if device_class in ("battery", "battery_value"):
                return SensorDeviceClass.BATTERY
    return None


def _get_unit_of_measurement(property_code: str, value: Any, device_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Get unit of measurement for sensor.
    
    Args:
        property_code: The property code (e.g., "temp_current")
        value: The property value
        device_data: Optional device data dict to check for temp_unit_convert
    """
    device_class = _get_sensor_device_class(property_code)
    
    if device_class == SensorDeviceClass.TEMPERATURE:
        # Check if device has temp_unit_convert property
        if device_data:
            unit_convert = device_data.get("temp_unit_convert", "c")
            if unit_convert and unit_convert.lower() == "f":
                return "°F"
        return "°C"
    if device_class == SensorDeviceClass.HUMIDITY:
        return "%"
    if device_class == SensorDeviceClass.BATTERY:
        if _is_numeric_value(value):
            return "%"
        return None
    
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya Unsupported Sensors sensor entities."""
    coordinator: ExtraTuyaSensorsDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]["coordinator"]
    device_ids = entry.data[CONF_DEVICES]
    discovered_devices = hass.data[DOMAIN][entry.entry_id].get("devices", {})
    
    entities = []
    
    sensor_codes = set()
    for codes in SENSOR_PROPERTY_CODES.values():
        sensor_codes.update(codes)
    
    for device_id in device_ids:
        device_info = discovered_devices.get(device_id, {})
        # Use Tuya customName first, then name, then fallback
        device_name = device_info.get("customName") or device_info.get("name", f"Device {device_id}")
        device_model = device_info.get("product_name", "Unknown")
        
        device_data = coordinator.data.get(device_id, {})
        
        _LOGGER.debug("Processing device %s (%s): %s", device_id, device_name, device_data)
        
        for property_code, value in device_data.items():
            property_code_lower = property_code.lower()
            
            # Log battery-related properties for debugging
            if "battery" in property_code_lower:
                _LOGGER.debug(
                    "Found battery property: code=%s, value=%s (type=%s), matches sensor codes=%s",
                    property_code,
                    value,
                    type(value).__name__,
                    property_code_lower in sensor_codes
                )
            
            # Check if this is a sensor property code
            if property_code_lower in sensor_codes:
                # For battery sensors, only set device_class if value is numeric
                # Home Assistant requires numeric values for battery device_class
                device_class = _get_sensor_device_class(property_code)
                if device_class == SensorDeviceClass.BATTERY and not _is_numeric_value(value):
                    # Don't set device_class for text battery values
                    entity = ExtraTuyaSensor(
                        coordinator=coordinator,
                        device_id=device_id,
                        device_name=device_name,
                        device_model=device_model,
                        property_code=property_code,
                        force_device_class=None,  # Override device_class
                    )
                else:
                    entity = ExtraTuyaSensor(
                        coordinator=coordinator,
                        device_id=device_id,
                        device_name=device_name,
                        device_model=device_model,
                        property_code=property_code,
                    )
                entities.append(entity)
            elif _is_numeric_value(value):
                entity = ExtraTuyaSensor(
                    coordinator=coordinator,
                    device_id=device_id,
                    device_name=device_name,
                    device_model=device_model,
                    property_code=property_code,
                )
                entities.append(entity)
    
    async_add_entities(entities)


class ExtraTuyaSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tuya sensor."""

    def __init__(
        self,
        coordinator: ExtraTuyaSensorsDataUpdateCoordinator,
        device_id: str,
        device_name: str,
        device_model: str,
        property_code: str,
        force_device_class: Optional[str] = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._device_model = device_model
        self._property_code = property_code
        
        friendly_name = _get_friendly_name(property_code)
        self._attr_name = f"{device_name} {friendly_name}"
        
        # Use slugified device name and friendly name for unique_id
        # This ensures entity IDs use custom names and friendly property names
        device_name_slug = slugify(device_name)
        friendly_name_slug = slugify(friendly_name)
        self._attr_unique_id = f"{device_name_slug}_{friendly_name_slug}"
        
        # Store the intended device class, but we'll check it dynamically
        # force_device_class can override (e.g., None for text battery values)
        if force_device_class is not None:
            self._intended_device_class = force_device_class
        else:
            device_class = _get_sensor_device_class(property_code)
            self._intended_device_class = device_class if device_class else None
        
        # Initialize device_class to None - will be set dynamically
        self._attr_device_class = None

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
    def device_class(self) -> Optional[str]:
        """Return device class, checking value type for battery sensors."""
        # For battery sensors, only return device_class if value is numeric
        if self._intended_device_class == SensorDeviceClass.BATTERY:
            device_data = self.coordinator.data.get(self._device_id, {})
            value = device_data.get(self._property_code)
            if value is not None and _is_numeric_value(value):
                return SensorDeviceClass.BATTERY
            # Text battery values should not have device_class
            return None
        
        # For other sensors, return the intended device class
        return self._intended_device_class

    @property
    def native_value(self) -> Optional[Union[float, str]]:
        """Return the state of the sensor."""
        device_data = self.coordinator.data.get(self._device_id, {})
        value = device_data.get(self._property_code)
        
        if value is None:
            return None
        
        if _is_numeric_value(value):
            num_value = float(value)
            
            # Get scale from device model to properly convert values
            # Scale indicates division factor: scale=1 means divide by 10^1=10, scale=0 means no scaling
            # Scales are cached in the API client and fetched during coordinator updates
            try:
                # Get cached scale (synchronous - scales are fetched during coordinator updates)
                scale = self.coordinator.client.get_cached_property_scale(
                    self._device_id, self._property_code
                )
                
                if scale is not None and scale > 0:
                    divisor = 10 ** scale
                    num_value = num_value / divisor
                    _LOGGER.debug(
                        "Applied scale %d (divide by %d) to %s: %s -> %s",
                        scale,
                        divisor,
                        self._property_code,
                        value,
                        num_value
                    )
            except Exception as e:
                _LOGGER.debug(
                    "Could not get scale for %s.%s, using raw value: %s",
                    self._device_id,
                    self._property_code,
                    e
                )
            
            return num_value
        
        # For battery text values, log what we're getting
        # (device_class should already be None if value is text, set during init)
        if "battery" in self._property_code.lower():
            _LOGGER.debug(
                "Battery sensor %s (%s) has non-numeric value: %s (type: %s)",
                self._device_id,
                self._property_code,
                value,
                type(value).__name__
            )
        
        return str(value)
    
    @property
    def state_class(self) -> Optional[str]:
        """Return state class for numeric sensors."""
        device_data = self.coordinator.data.get(self._device_id, {})
        value = device_data.get(self._property_code)
        
        # Only set state_class for numeric values
        if not _is_numeric_value(value):
            return None
        
        # All numeric sensors should have state_class
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        device_data = self.coordinator.data.get(self._device_id, {})
        value = device_data.get(self._property_code)
        
        # Check device class using the property (which handles battery text values)
        device_class = self.device_class
        
        if device_class == SensorDeviceClass.BATTERY:
            # Only return unit for numeric battery values
            if not _is_numeric_value(value):
                return None
        
        return _get_unit_of_measurement(self._property_code, value, device_data)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "device_id": self._device_id,
            "property_code": self._property_code,
        }
