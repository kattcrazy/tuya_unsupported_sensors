"""Config flow for Tuya Unsupported Sensors integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REGION,
    CONF_DEVICES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    DOMAIN,
    REGIONS,
    TRIAL_MAX_DEVICES,
    TRIAL_MAX_API_CALLS_PER_MONTH,
    TRIAL_MAX_MESSAGES_PER_MONTH,
    SECONDS_PER_MONTH,
    MESSAGES_PER_API_CALL,
)
from .tuya_api import TuyaAPIClient

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


def _calculate_monthly_usage(num_devices: int, update_interval: int) -> tuple[int, int]:
    """Calculate monthly API calls and messages based on device count and update interval.
    
    Args:
        num_devices: Number of devices being monitored.
        update_interval: Update interval in seconds.
        
    Returns:
        Tuple of (api_calls_per_month, messages_per_month).
    """
    if update_interval <= 0:
        return (0, 0)
    
    api_calls_per_month = int((SECONDS_PER_MONTH / update_interval) * num_devices)
    messages_per_month = int(api_calls_per_month * MESSAGES_PER_API_CALL)
    
    return (api_calls_per_month, messages_per_month)


def _calculate_minimum_interval(num_devices: int) -> int:
    """Calculate minimum update interval to stay within IOT CORE TRIAL PLAN limits.
    
    Formula:
        API calls limit: interval >= (SECONDS_PER_MONTH × num_devices) / TRIAL_MAX_API_CALLS_PER_MONTH
        Messages limit: interval >= (SECONDS_PER_MONTH × num_devices × MESSAGES_PER_API_CALL) / TRIAL_MAX_MESSAGES_PER_MONTH
    
    With actual constants:
        API calls: interval >= (2,592,000 × num_devices) / 26,000 ≈ 99.69 × num_devices
        Messages: interval >= (2,592,000 × num_devices × 2.6) / 68,000 ≈ 99.11 × num_devices
    
    The API calls limit is slightly more restrictive (requires ~99.69s per device vs ~99.11s),
    so we use the maximum of both to ensure both limits are respected.
    
    Args:
        num_devices: Number of devices being monitored.
        
    Returns:
        Minimum update interval in seconds needed to stay within limits.
    """
    if num_devices <= 0:
        return MIN_UPDATE_INTERVAL
    
    # Calculate based on API calls limit: (2,592,000 × num_devices) / 26,000
    min_interval_api = (SECONDS_PER_MONTH * num_devices) / TRIAL_MAX_API_CALLS_PER_MONTH
    
    # Calculate based on messages limit: (2,592,000 × num_devices × 2.6) / 68,000
    min_interval_messages = (SECONDS_PER_MONTH * num_devices * MESSAGES_PER_API_CALL) / TRIAL_MAX_MESSAGES_PER_MONTH
    
    # Use the larger of the two (more restrictive limit) to ensure both limits are respected
    min_interval = max(min_interval_api, min_interval_messages)
    
    # Round up to nearest integer and ensure it's at least MIN_UPDATE_INTERVAL
    min_interval = max(int(min_interval) + (1 if min_interval % 1 > 0 else 0), MIN_UPDATE_INTERVAL)
    
    return min_interval


def _check_trial_limits(num_devices: int, update_interval: int) -> tuple[bool, str]:
    """Check if configuration exceeds IOT CORE TRIAL PLAN limits.
    
    Args:
        num_devices: Number of devices being monitored.
        update_interval: Update interval in seconds.
        
    Returns:
        Tuple of (exceeds_limits, warning_message).
        If exceeds_limits is True, warning_message contains the warning text with minimum interval.
    """
    warnings = []
    
    # Check device count limit
    if num_devices > TRIAL_MAX_DEVICES:
        warnings.append(f"device count ({num_devices}) exceeds maximum of {TRIAL_MAX_DEVICES}")
    
    # Calculate monthly usage
    api_calls_per_month, messages_per_month = _calculate_monthly_usage(num_devices, update_interval)
    
    # Check API calls limit
    if api_calls_per_month > TRIAL_MAX_API_CALLS_PER_MONTH:
        warnings.append(f"API calls ({api_calls_per_month:,}) exceeds monthly limit of {TRIAL_MAX_API_CALLS_PER_MONTH:,}")
    
    # Check messages limit
    if messages_per_month > TRIAL_MAX_MESSAGES_PER_MONTH:
        warnings.append(f"messages ({messages_per_month:,}) exceeds monthly limit of {TRIAL_MAX_MESSAGES_PER_MONTH:,}")
    
    if warnings:
        min_interval = _calculate_minimum_interval(num_devices)
        warning_msg = f"Warning: Your selection of {update_interval} second intervals with {num_devices} device(s) will go over the IOT CORE TRIAL PLAN limits. Recommended minimum interval: {min_interval} seconds"
        return (True, warning_msg)
    
    return (False, "")


def _get_existing_tuya_device_ids(hass: HomeAssistant) -> set:
    """Get device IDs from other enabled Tuya integrations.
    
    Only checks devices that belong to enabled Tuya config entries,
    have active entities (not unsupported), and only matches by device ID
    (not by name) to avoid false positives.
    
    Args:
        hass: Home Assistant instance.
        
    Returns:
        Set of device IDs that are already added via other Tuya integrations.
    """
    existing_ids = set()
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    config_entry_registry = hass.config_entries
    
    # Check for devices from other Tuya integrations
    tuya_domains = ["tuya", "localtuya", "tuyalocal", "extratuya"]
    
    # Get set of enabled config entry IDs for Tuya integrations
    enabled_entry_ids = set()
    for entry in config_entry_registry.async_entries():
        if entry.domain in tuya_domains:
            # Only count if entry is not disabled and not unsupported
            if entry.disabled_by is None and not getattr(entry, 'pref_disable_new_entities', False):
                enabled_entry_ids.add(entry.entry_id)
    
    for device_entry in device_registry.devices.values():
        # Only check devices that belong to enabled config entries
        device_entry_ids = device_entry.config_entries
        
        # Check if any of the device's config entries are enabled Tuya integrations
        has_enabled_tuya_entry = False
        for entry_id in device_entry_ids:
            if entry_id in enabled_entry_ids:
                has_enabled_tuya_entry = True
                break
        
        if not has_enabled_tuya_entry:
            continue
        
        # Check if device has any active entities (not unsupported)
        # Unsupported devices have no entities or all entities are disabled
        device_entities = er.async_entries_for_device(
            entity_registry, device_entry.id
        )
        
        # Filter out disabled entities and check if any active entities remain
        active_entities = [
            entity for entity in device_entities
            if entity.disabled_by is None
        ]
        
        # Skip devices with no active entities (unsupported devices)
        if not active_entities:
            continue
        
        # Only check devices that have Tuya domain identifiers
        # This ensures we only match actual Tuya devices, not devices with similar names
        for identifier in device_entry.identifiers:
            if isinstance(identifier, tuple) and len(identifier) >= 2:
                domain = identifier[0]
                device_id = identifier[1]
                
                # Only add device IDs from Tuya integrations
                # Don't match by name to avoid false positives with non-Tuya devices
                if domain in tuya_domains:
                    existing_ids.add(str(device_id))
                    existing_ids.add(str(device_id).lower())
    
    return existing_ids


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya Unsupported Sensors."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._client_id: Optional[str] = None
        self._client_secret: Optional[str] = None
        self._region: Optional[str] = None
        self._devices: Optional[list] = None
        self._discovered_devices: Optional[list] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step - region selection."""
        if user_input is None:
            region_options = {
                "us": "US (Western)",
                "us_east": "US (Eastern)",
                "eu": "EU (Central)",
                "eu_west": "EU (Western)",
                "cn": "China",
                "in": "India",
                "sg": "Singapore",
                "jp": "Japan",
            }
            
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_REGION): vol.In(region_options),
                }
            )
            
            return self.async_show_form(
                step_id="user",
                data_schema=data_schema,
            )
        
        self._region = user_input[CONF_REGION]
        return await self.async_step_credentials()

    async def async_step_credentials(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle credentials input step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            self._client_id = user_input[CONF_CLIENT_ID]
            self._client_secret = user_input[CONF_CLIENT_SECRET]
            
            try:
                await self._test_connection()
                return await self.async_step_discover_devices()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        
        data_schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID, default=self._client_id or ""): str,
                vol.Required(CONF_CLIENT_SECRET, default=self._client_secret or ""): cv.string,
            }
        )
        
        return self.async_show_form(
            step_id="credentials",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_discover_devices(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle device discovery step."""
        if user_input is None:
            try:
                client = TuyaAPIClient(
                    self._client_id,
                    self._client_secret,
                    self._region,
                )
                self._discovered_devices = await client.discover_devices()
                
                if not self._discovered_devices:
                    return self.async_abort(reason="no_devices")
                
            except Exception as err:
                _LOGGER.exception("Error discovering devices: %s", err)
                return self.async_abort(reason="discovery_failed")
        
        return await self.async_step_select_devices()

    async def async_step_select_devices(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle device selection step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            selected_devices = user_input.get(CONF_DEVICES, [])
            
            if not selected_devices:
                errors["base"] = "no_devices_selected"
            else:
                if len(selected_devices) > TRIAL_MAX_DEVICES:
                    errors["base"] = f"Device count ({len(selected_devices)}) exceeds IOT CORE TRIAL PLAN limit of {TRIAL_MAX_DEVICES} devices"
                else:
                    self._devices = selected_devices
                    return await self.async_step_update_interval()
        
        # Get device IDs already added via other Tuya integrations
        existing_device_ids = _get_existing_tuya_device_ids(self.hass)
        
        # Separate devices into already-added and not-added
        unadded_devices = []
        added_devices = []
        
        for device in self._discovered_devices or []:
            device_id = device.get("id", "")
            device_name = device.get("customName") or device.get("name", "Unknown Device")
            
            # Check if device is already added by Tuya device ID only
            # Don't match by name to avoid false positives with non-Tuya devices
            is_added = (
                device_id in existing_device_ids or
                device_id.lower() in existing_device_ids
            )
            
            device_info = {
                "id": device_id,
                "name": device_name,
                "is_added": is_added,
            }
            
            if is_added:
                added_devices.append(device_info)
            else:
                unadded_devices.append(device_info)
        
        # Build device options: unadded first, then added (with indicators)
        device_options = {}
        
        # Add unadded devices first (priority)
        for device in unadded_devices:
            device_options[device["id"]] = device["name"]
        
        # Add already-added devices with indicator
        for device in added_devices:
            device_options[device["id"]] = f"{device['name']} [Already added via another integration]"
        
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICES,
                    default=self._devices or [],
                ): cv.multi_select(device_options),
            }
        )
        
        info_text = "We recommend selecting only devices that aren't already added via other Tuya integrations."
        if added_devices:
            info_text += f" {len(unadded_devices)} device(s) not yet added, {len(added_devices)} already added."
        
        return self.async_show_form(
            step_id="select_devices",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": info_text,
            },
        )

    async def async_step_update_interval(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle update interval step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            update_interval = user_input.get(CONF_UPDATE_INTERVAL)
            if update_interval is not None:
                try:
                    update_interval = int(update_interval)
                    if update_interval < MIN_UPDATE_INTERVAL or update_interval > MAX_UPDATE_INTERVAL:
                        errors[CONF_UPDATE_INTERVAL] = f"Must be between {MIN_UPDATE_INTERVAL} and {MAX_UPDATE_INTERVAL} seconds"
                    else:
                        num_devices = len(self._devices) if self._devices else 0
                        exceeds_limits, warning_msg = _check_trial_limits(num_devices, update_interval)
                        if exceeds_limits:
                            errors[CONF_UPDATE_INTERVAL] = warning_msg
                        else:
                            return self.async_create_entry(
                                title=f"Tuya Unsupported Sensors ({self._region.upper()})",
                                data={
                                    CONF_CLIENT_ID: self._client_id,
                                    CONF_CLIENT_SECRET: self._client_secret,
                                    CONF_REGION: self._region,
                                    CONF_DEVICES: self._devices,
                                    CONF_UPDATE_INTERVAL: update_interval,
                                },
                            )
                except (ValueError, TypeError):
                    errors[CONF_UPDATE_INTERVAL] = "Must be a valid number"
        
        num_devices = len(self._devices) if self._devices else 0
        exceeds_limits, warning_msg = _check_trial_limits(num_devices, DEFAULT_UPDATE_INTERVAL)
        
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                    description={"suffix": "seconds"},
                ): cv.positive_int,
            }
        )
        
        description = ""
        if exceeds_limits:
            description = warning_msg
        
        return self.async_show_form(
            step_id="update_interval",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"info": description},
        )
        

    async def _test_connection(self) -> None:
        """Test connection to Tuya API."""
        try:
            client = TuyaAPIClient(
                self._client_id,
                self._client_secret,
                self._region,
            )
            await client.get_access_token()
        except ValueError as err:
            if "invalid" in str(err).lower() or "auth" in str(err).lower():
                raise InvalidAuth from err
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.exception("Error testing connection: %s", err)
            raise CannotConnect from err

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "OptionsFlowHandler":
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Tuya Unsupported Sensors."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._discovered_devices: Optional[list] = None

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options - show menu."""
        if user_input is not None:
            next_step = user_input.get("next_step")
            if next_step == "devices":
                return await self.async_step_discover_devices()
            elif next_step == "interval":
                return await self.async_step_update_interval()
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("next_step", default="devices"): vol.In({
                        "devices": "Update Devices",
                        "interval": "Update Interval",
                    }),
                }
            ),
        )

    async def async_step_discover_devices(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle device discovery step."""
        if user_input is None:
            try:
                client_id = self.config_entry.data[CONF_CLIENT_ID]
                client_secret = self.config_entry.data[CONF_CLIENT_SECRET]
                region = self.config_entry.data[CONF_REGION]
                
                client = TuyaAPIClient(
                    client_id,
                    client_secret,
                    region,
                )
                self._discovered_devices = await client.discover_devices()
                
                if not self._discovered_devices:
                    return self.async_abort(reason="no_devices")
                
            except Exception as err:
                _LOGGER.exception("Error discovering devices: %s", err)
                return self.async_abort(reason="discovery_failed")
        
        return await self.async_step_select_devices()

    async def async_step_select_devices(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle device selection step."""
        errors: Dict[str, str] = {}
        current_devices = self.config_entry.data.get(CONF_DEVICES, [])
        
        if user_input is not None:
            selected_devices = user_input.get(CONF_DEVICES, [])
            
            if not selected_devices:
                errors["base"] = "no_devices_selected"
            else:
                if len(selected_devices) > TRIAL_MAX_DEVICES:
                    errors["base"] = f"Device count ({len(selected_devices)}) exceeds IOT CORE TRIAL PLAN limit of {TRIAL_MAX_DEVICES} devices"
                else:
                    # Update config entry with new device list
                    new_data = {**self.config_entry.data}
                    new_data[CONF_DEVICES] = selected_devices
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )
                    return self.async_create_entry(title="", data={})
        
        # Get device IDs already added via other Tuya integrations
        existing_device_ids = _get_existing_tuya_device_ids(self.hass)
        
        # Separate devices into already-added and not-added
        unadded_devices = []
        added_devices = []
        
        for device in self._discovered_devices or []:
            device_id = device.get("id", "")
            device_name = device.get("customName") or device.get("name", "Unknown Device")
            
            # Check if device is already added by Tuya device ID only
            # Don't match by name to avoid false positives with non-Tuya devices
            is_added = (
                device_id in existing_device_ids or
                device_id.lower() in existing_device_ids
            )
            
            device_info = {
                "id": device_id,
                "name": device_name,
                "is_added": is_added,
            }
            
            if is_added:
                added_devices.append(device_info)
            else:
                unadded_devices.append(device_info)
        
        # Build device options: unadded first, then added (with indicators)
        device_options = {}
        
        # Add unadded devices first (priority)
        for device in unadded_devices:
            device_options[device["id"]] = device["name"]
        
        # Add already-added devices with indicator
        for device in added_devices:
            device_options[device["id"]] = f"{device['name']} [Already added via another integration]"
        
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICES,
                    default=current_devices,
                ): cv.multi_select(device_options),
            }
        )
        
        info_text = "We recommend selecting only devices that aren't already added via other Tuya integrations."
        if added_devices:
            info_text += f" {len(unadded_devices)} device(s) not yet added, {len(added_devices)} already added."
        
        return self.async_show_form(
            step_id="select_devices",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": info_text,
            },
        )

    async def async_step_update_interval(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle update interval step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            update_interval = user_input.get(CONF_UPDATE_INTERVAL)
            if update_interval is not None:
                try:
                    update_interval = int(update_interval)
                    if update_interval < MIN_UPDATE_INTERVAL or update_interval > MAX_UPDATE_INTERVAL:
                        errors[CONF_UPDATE_INTERVAL] = f"Must be between {MIN_UPDATE_INTERVAL} and {MAX_UPDATE_INTERVAL} seconds"
                    else:
                        num_devices = len(self.config_entry.data.get(CONF_DEVICES, []))
                        exceeds_limits, warning_msg = _check_trial_limits(num_devices, update_interval)
                        if exceeds_limits:
                            errors[CONF_UPDATE_INTERVAL] = warning_msg
                        else:
                            new_data = {**self.config_entry.data}
                            new_data[CONF_UPDATE_INTERVAL] = update_interval
                            self.hass.config_entries.async_update_entry(
                                self.config_entry, data=new_data
                            )
                            return self.async_create_entry(title="", data={})
                except (ValueError, TypeError):
                    errors[CONF_UPDATE_INTERVAL] = "Must be a valid number"
        
        current_interval = self.config_entry.data.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        
        num_devices = len(self.config_entry.data.get(CONF_DEVICES, []))
        exceeds_limits, warning_msg = _check_trial_limits(num_devices, current_interval)
        
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=current_interval,
                    description={"suffix": "seconds"},
                ): cv.positive_int,
            }
        )
        
        description = ""
        if exceeds_limits:
            description = warning_msg
        
        return self.async_show_form(
            step_id="update_interval",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"info": description},
        )
