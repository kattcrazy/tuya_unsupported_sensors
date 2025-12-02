"""Data update coordinator for Tuya Unsupported Sensors integration."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .tuya_api import TuyaAPIClient

_LOGGER = logging.getLogger(__name__)


class ExtraTuyaSensorsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Tuya API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TuyaAPIClient,
        device_ids: List[str],
        update_interval: int,
    ) -> None:
        """Initialize coordinator.
        
        Args:
            hass: Home Assistant instance.
            client: Tuya API client instance.
            device_ids: List of device IDs to monitor.
            update_interval: Update interval in seconds.
        """
        self.client = client
        self.device_ids = device_ids
        self.update_interval_seconds = update_interval
        
        update_interval_timedelta = timedelta(seconds=update_interval)
        
        # Track when each device was last successfully updated
        self._last_successful_update: Dict[str, datetime] = {}
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval_timedelta,
        )

    async def _async_update_data(self) -> Dict[str, Dict[str, Any]]:
        """Fetch data from Tuya API.
        
        Returns:
            Dictionary mapping device_id to device properties.
            Example: {
                "device_id_1": {"temp": 25.5, "humidity": 60},
                "device_id_2": {"contact": True, "battery": 85}
            }
            
        Raises:
            UpdateFailed: If update fails.
        """
        data: Dict[str, Dict[str, Any]] = {}
        token_error_occurred = False
        now = datetime.now()
        max_stale_time = timedelta(seconds=self.update_interval_seconds)  # Allow 1x update interval for stale data
        
        for device_id in self.device_ids:
            try:
                properties = await self.client.get_device_properties(device_id)
                data[device_id] = properties
                self._last_successful_update[device_id] = now
                _LOGGER.debug("Updated data for device %s: %s", device_id, properties)
                
                # Fetch and cache property scales if not already cached
                # This ensures scales are available for value conversion
                if device_id not in self.client._property_scales:
                    try:
                        model_response = await self.client.get_device_model(device_id)
                        scales = self.client._extract_property_scales(model_response)
                        self.client._property_scales[device_id] = scales
                        _LOGGER.debug("Cached scales for device %s: %s", device_id, scales)
                    except Exception as scale_err:
                        _LOGGER.debug("Could not fetch scales for device %s: %s", device_id, scale_err)
                        # Continue without scales - values will be used as-is
                        
            except ValueError as err:
                error_str = str(err)
                # Check if this is a token error (1010)
                if "1010" in error_str or "token invalid" in error_str.lower():
                    if not token_error_occurred:
                        # Get token age for detailed logging
                        token_age = None
                        if self.client._token_expires_at:
                            token_age = (now - (self.client._token_expires_at - timedelta(seconds=7200))).total_seconds() / 3600
                        
                        _LOGGER.warning(
                            "ERROR 1010 (Token Invalid) detected for device %s. "
                            "REASON: Tuya API access tokens expire after ~2 hours. "
                            "Token age: %s hours. "
                            "ACTION: Clearing cached token and refreshing. "
                            "Sensors may show 'unknown' state temporarily until token refresh completes.",
                            device_id,
                            f"{token_age:.2f}" if token_age else "unknown"
                        )
                        self.client._clear_token()
                        token_error_occurred = True
                    # Check if we can keep previous data (not too stale)
                    if self.data is not None and device_id in self.data and device_id in self._last_successful_update:
                        time_since_update = now - self._last_successful_update[device_id]
                        if time_since_update <= max_stale_time:
                            _LOGGER.debug("Keeping previous data for device %s due to token error (last update: %s ago)", 
                                        device_id, time_since_update)
                            data[device_id] = self.data.get(device_id, {})
                        else:
                            _LOGGER.error(
                                "Device %s sensors showing 'unknown' state. "
                                "REASON: Previous data is too stale (%s old, max allowed: %s). "
                                "Token refresh is in progress. Sensors will update once token is refreshed.",
                                device_id,
                                time_since_update,
                                max_stale_time
                            )
                            data[device_id] = {}
                    else:
                        _LOGGER.error(
                            "Device %s sensors showing 'unknown' state. "
                            "REASON: No previous data available and token expired (1010). "
                            "Token refresh is in progress. Sensors will update once token is refreshed.",
                            device_id
                        )
                        data[device_id] = {}
                else:
                    _LOGGER.error(
                        "Error updating device %s: %s. "
                        "This is a non-token API error. Check API credentials and device connectivity.",
                        device_id,
                        err
                    )
                    # Check if we can keep previous data (not too stale)
                    if self.data is not None and device_id in self.data and device_id in self._last_successful_update:
                        time_since_update = now - self._last_successful_update[device_id]
                        if time_since_update <= max_stale_time:
                            _LOGGER.debug("Keeping previous data for device %s due to error (last update: %s ago)", 
                                        device_id, time_since_update)
                            data[device_id] = self.data.get(device_id, {})
                        else:
                            _LOGGER.error(
                                "Device %s sensors showing 'unknown' state. "
                                "REASON: Previous data is too stale (%s old, max allowed: %s) and API error occurred: %s",
                                device_id,
                                time_since_update,
                                max_stale_time,
                                err
                            )
                            data[device_id] = {}
                    else:
                        _LOGGER.error(
                            "Device %s sensors showing 'unknown' state. "
                            "REASON: No previous data available and API error occurred: %s",
                            device_id,
                            err
                        )
                        data[device_id] = {}
            except Exception as err:
                _LOGGER.error(
                    "Unexpected error updating device %s: %s. "
                    "This may indicate a network issue, API problem, or integration bug.",
                    device_id,
                    err,
                    exc_info=True
                )
                # Check if we can keep previous data (not too stale)
                if self.data is not None and device_id in self.data and device_id in self._last_successful_update:
                    time_since_update = now - self._last_successful_update[device_id]
                    if time_since_update <= max_stale_time:
                        _LOGGER.debug("Keeping previous data for device %s due to error (last update: %s ago)", 
                                    device_id, time_since_update)
                        data[device_id] = self.data.get(device_id, {})
                    else:
                        _LOGGER.error(
                            "Device %s sensors showing 'unknown' state. "
                            "REASON: Previous data is too stale (%s old, max allowed: %s) and unexpected error occurred: %s",
                            device_id,
                            time_since_update,
                            max_stale_time,
                            err
                        )
                        data[device_id] = {}
                else:
                    _LOGGER.error(
                        "Device %s sensors showing 'unknown' state. "
                        "REASON: No previous data available and unexpected error occurred: %s",
                        device_id,
                        err
                    )
                    data[device_id] = {}
        
        # If we had token errors, retry once for all devices
        if token_error_occurred:
            _LOGGER.info(
                "Retrying device updates after token refresh. "
                "This should resolve the 'unknown' sensor states if token refresh succeeds."
            )
            retry_data: Dict[str, Dict[str, Any]] = {}
            retry_now = datetime.now()
            for device_id in self.device_ids:
                if device_id not in data or not data[device_id]:
                    try:
                        properties = await self.client.get_device_properties(device_id)
                        retry_data[device_id] = properties
                        self._last_successful_update[device_id] = retry_now
                        _LOGGER.info(
                            "Device %s successfully updated after token refresh. "
                            "Sensors should now show current values instead of 'unknown'.",
                            device_id
                        )
                    except Exception as err:
                        error_str = str(err)
                        if "1010" in error_str or "token invalid" in error_str.lower():
                            _LOGGER.error(
                                "Token refresh retry failed for device %s: Still getting 1010 error. "
                                "REASON: Token refresh may have failed or new token is also invalid. "
                                "Check API credentials. Sensors will remain 'unknown' until next successful update.",
                                device_id
                            )
                        else:
                            _LOGGER.error(
                                "Token refresh retry failed for device %s: %s. "
                                "REASON: Non-token error after token refresh. Sensors will remain 'unknown'.",
                                device_id,
                                err
                            )
                        # Check if we can keep previous data (not too stale)
                        if self.data is not None and device_id in self.data and device_id in self._last_successful_update:
                            time_since_update = retry_now - self._last_successful_update[device_id]
                            if time_since_update <= max_stale_time:
                                retry_data[device_id] = self.data.get(device_id, {})
                            else:
                                _LOGGER.error(
                                    "Device %s sensors showing 'unknown' state. "
                                    "REASON: Retry failed and previous data is too stale (%s old).",
                                    device_id,
                                    time_since_update
                                )
                                retry_data[device_id] = {}
                        else:
                            _LOGGER.error(
                                "Device %s sensors showing 'unknown' state. "
                                "REASON: Retry failed and no previous data available.",
                                device_id
                            )
                            retry_data[device_id] = {}
                else:
                    retry_data[device_id] = data[device_id]
            data = retry_data
        
        if not data:
            raise UpdateFailed("Failed to update any devices")
        
        return data
