"""Data update coordinator for Tuya Unsupported Sensors integration."""

import logging
from datetime import timedelta
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
            update_interval: Update interval in minutes.
        """
        self.client = client
        self.device_ids = device_ids
        
        update_interval_timedelta = timedelta(minutes=update_interval)
        
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
        
        for device_id in self.device_ids:
            try:
                properties = await self.client.get_device_properties(device_id)
                data[device_id] = properties
                _LOGGER.debug("Updated data for device %s: %s", device_id, properties)
            except Exception as err:
                _LOGGER.error("Error updating device %s: %s", device_id, err)
                data[device_id] = {}
        
        if not data:
            raise UpdateFailed("Failed to update any devices")
        
        return data
