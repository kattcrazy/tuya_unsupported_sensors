"""Tuya API client for Tuya Unsupported Sensors integration."""

import hashlib
import hmac
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from .const import (
    EMPTY_BODY,
    LOGIN_URL,
    DEVICE_LIST_URL,
    PROPERTIES_URL,
    MODEL_URL,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)


class TuyaAPIClient:
    """Client for interacting with Tuya Cloud API."""

    def __init__(self, client_id: str, client_secret: str, region: str) -> None:
        """Initialize Tuya API client.
        
        Args:
            client_id: Tuya API client ID (Access ID)
            client_secret: Tuya API client secret (Access Key)
            region: Region code (us, eu, cn, etc.)
        """
        self._client_id = client_id
        self._client_secret = client_secret
        
        if region not in REGIONS:
            raise ValueError(f"Invalid region: {region}. Must be one of {list(REGIONS.keys())}")
        
        self._region = region
        self._base_url = REGIONS[region]
        
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._uid: Optional[str] = None
        
        # Cache for property scales: {device_id: {property_code: scale}}
        self._property_scales: Dict[str, Dict[str, int]] = {}
        
        _LOGGER.debug("Initialized TuyaAPIClient for region: %s", region)
    
    def _clear_token(self) -> None:
        """Clear cached access token to force refresh on next request."""
        self._access_token = None
        self._token_expires_at = None
        _LOGGER.debug("Cleared cached access token")
    
    def _is_token_invalid_error(self, json_result: Dict[str, Any]) -> bool:
        """Check if API response indicates token is invalid.
        
        Args:
            json_result: Parsed JSON response from API.
            
        Returns:
            True if token is invalid, False otherwise.
        """
        if "success" in json_result and not json_result.get("success"):
            error_code = json_result.get("code")
            error_msg = json_result.get("msg", "").lower()
            # Check for token invalid error (code 1010 or message contains "token")
            return error_code == 1010 or "token" in error_msg
        return False

    @staticmethod
    def _get_timestamp(now: Optional[datetime] = None) -> str:
        """Generate timestamp in milliseconds.
        
        Args:
            now: Optional datetime object. Defaults to current time.
            
        Returns:
            Timestamp as string in milliseconds.
        """
        if now is None:
            now = datetime.now()
        return str(int(now.timestamp() * 1000))

    @staticmethod
    def _get_sign(payload: str, key: str) -> str:
        """Generate HMAC-SHA256 signature.
        
        Args:
            payload: String to sign.
            key: Secret key for signing.
            
        Returns:
            Uppercase hexadecimal signature.
        """
        byte_key = bytes(key, "UTF-8")
        message = payload.encode("UTF-8")
        sign = hmac.new(byte_key, message, hashlib.sha256).hexdigest()
        return sign.upper()

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> tuple[aiohttp.ClientResponse, str]:
        """Make async HTTP request to Tuya API.
        
        Args:
            url: Full URL to request (including base URL).
            method: HTTP method (GET, POST, etc.). Defaults to GET.
            params: Query parameters as dictionary.
            headers: Request headers as dictionary.
            body: Request body as string (for POST requests).
            
        Returns:
            Tuple of (response object, response body as string).
            
        Raises:
            aiohttp.ClientError: For HTTP/client errors.
            asyncio.TimeoutError: For timeout errors.
        """
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers or {},
                    data=body,
                ) as response:
                    response_text = await response.text()
                    response.raise_for_status()
                    return response, response_text
            except aiohttp.ClientError as error:
                _LOGGER.error("HTTP request failed: %s", error)
                raise
            except asyncio.TimeoutError as error:
                _LOGGER.error("Request timeout: %s", error)
                raise

    async def get_access_token(self) -> str:
        """Get access token, refreshing if necessary.
        
        Checks if cached token is still valid (not expired and not expiring in < 5 minutes).
        If not valid, requests a new token from Tuya API.
        
        Returns:
            Access token string.
            
        Raises:
            aiohttp.ClientError: If token request fails.
            ValueError: If API response is invalid.
        """
        now = datetime.now()
        
        if self._access_token and self._token_expires_at:
            time_until_expiry = (self._token_expires_at - now).total_seconds()
            if time_until_expiry > 300:
                _LOGGER.debug("Using cached access token (expires in %d seconds)", time_until_expiry)
                return self._access_token
        
        _LOGGER.debug("Requesting new access token")
        
        timestamp = self._get_timestamp(now)
        string_to_sign = (
            self._client_id + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + LOGIN_URL
        )
        signed_string = self._get_sign(string_to_sign, self._client_secret)
        
        headers = {
            "client_id": self._client_id,
            "sign": signed_string,
            "t": timestamp,
            "mode": "cors",
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json",
        }
        
        url = self._base_url + LOGIN_URL
        _, response_text = await self._make_request(url, method="GET", headers=headers)
        
        try:
            json_result = json.loads(response_text)
            if "result" not in json_result:
                raise ValueError(f"Invalid API response: {json_result}")
            
            result = json_result["result"]
            access_token = result.get("access_token")
            expires_in = result.get("expires_in", 7200)
            uid = result.get("uid")
            
            if not access_token:
                raise ValueError(f"Access token not found in response: {result}")
            
            self._access_token = access_token
            self._token_expires_at = now + timedelta(seconds=expires_in)
            if uid:
                self._uid = uid
                _LOGGER.debug("UID obtained from token: %s", uid)
            
            _LOGGER.debug(
                "Access token obtained, expires in %d seconds (will refresh when < 5 minutes remaining)",
                expires_in,
            )
            
            return self._access_token
            
        except json.JSONDecodeError as error:
            _LOGGER.error("Failed to parse token response: %s", error)
            raise ValueError(f"Invalid JSON response: {response_text}") from error

    async def discover_devices(self) -> List[Dict[str, Any]]:
        """Discover all devices associated with the API credentials.
        
        Uses the v2.0 API endpoint with pagination support.
        
        Returns:
            List of device dictionaries containing:
            - id: Device ID
            - name: Device name (from customName or name field)
            - product_id: Product identifier
            - product_name: Product name/model
            - Other device metadata
            
        Raises:
            aiohttp.ClientError: If API request fails.
            ValueError: If API response is invalid.
        """
        all_devices: List[Dict[str, Any]] = []
        last_id: Optional[str] = None
        page_size = 20  # Maximum allowed by API
        retry_count = 0
        max_retries = 1
        
        while True:
            access_token = await self.get_access_token()
            # Build query parameters
            params: Dict[str, Any] = {"page_size": page_size}
            if last_id:
                params["last_id"] = last_id
            
            # Build URL with query parameters
            url_path = DEVICE_LIST_URL
            query_parts = []
            for key, value in sorted(params.items()):  # Sort for consistent signature
                query_parts.append(f"{key}={value}")
            query_string = "&".join(query_parts)
            
            # Include query params in signature
            url_path_with_params = url_path + "?" + query_string if query_string else url_path
            
            timestamp = self._get_timestamp()
            string_to_sign = (
                self._client_id + access_token + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + url_path_with_params
            )
            signed_string = self._get_sign(string_to_sign, self._client_secret)
            
            headers = {
                "client_id": self._client_id,
                "sign": signed_string,
                "access_token": access_token,
                "t": timestamp,
                "mode": "cors",
                "sign_method": "HMAC-SHA256",
                "Content-Type": "application/json",
            }
            
            url = self._base_url + url_path_with_params
            
            try:
                _, response_text = await self._make_request(url, method="GET", headers=headers)
            except Exception as error:
                _LOGGER.error("Failed to make device discovery request: %s", error)
                raise
            
            try:
                json_result = json.loads(response_text)
                
                # Check for token invalid error and retry with fresh token
                if self._is_token_invalid_error(json_result):
                    if retry_count < max_retries:
                        _LOGGER.warning("Token invalid during device discovery, clearing cache and retrying with fresh token")
                        self._clear_token()
                        retry_count += 1
                        last_id = None  # Reset pagination
                        continue
                    else:
                        error_msg = json_result.get("msg", "Unknown error")
                        error_code = json_result.get("code", "unknown")
                        raise ValueError(f"Tuya API error after token refresh: {error_msg} (code: {error_code})")
                
                # Reset retry count on successful request
                retry_count = 0
                
                # Check for other API errors in response
                if "success" in json_result and not json_result["success"]:
                    error_msg = json_result.get("msg", "Unknown error")
                    error_code = json_result.get("code", "unknown")
                    _LOGGER.error("Tuya API error: %s (code: %s)", error_msg, error_code)
                    raise ValueError(f"Tuya API error: {error_msg} (code: {error_code})")
                
                if "result" not in json_result:
                    _LOGGER.error("Invalid API response structure: %s", json_result)
                    raise ValueError(f"Invalid API response: {json_result}")
                
                devices = json_result["result"]
                
                if not isinstance(devices, list):
                    _LOGGER.error("Expected list of devices, got %s: %s", type(devices), devices)
                    raise ValueError(f"Expected list of devices, got: {type(devices)}")
                
                if not devices:
                    # No more devices to fetch
                    break
                
                # Normalize device data to match expected format
                normalized_devices = []
                for device in devices:
                    normalized_device = {
                        "id": device.get("id"),
                        "name": device.get("customName") or device.get("name", ""),
                        "product_id": device.get("productId", ""),
                        "product_name": device.get("productName", ""),
                    }
                    # Include all original fields for reference
                    normalized_device.update(device)
                    normalized_devices.append(normalized_device)
                
                all_devices.extend(normalized_devices)
                
                # Check if we need to fetch more pages
                if len(devices) < page_size:
                    # Last page
                    break
                
                # Get last device ID for pagination
                last_id = devices[-1].get("id")
                if not last_id:
                    break
                
                _LOGGER.debug("Fetched %d devices, continuing pagination...", len(devices))
                
            except json.JSONDecodeError as error:
                _LOGGER.error("Failed to parse device list response. Response text: %s", response_text)
                raise ValueError(f"Invalid JSON response: {response_text}") from error
        
        _LOGGER.debug("Discovered %d total devices", len(all_devices))
        return all_devices

    async def get_device_properties(self, device_id: str) -> Dict[str, Any]:
        """Get device properties/sensor values for a specific device.
        
        Args:
            device_id: Tuya device ID.
            
        Returns:
            Dictionary mapping property codes to their values.
            Example: {"temp": 25.5, "humidity": 60, "battery": 85}
            
        Raises:
            aiohttp.ClientError: If API request fails.
            ValueError: If API response is invalid or device_id is empty.
        """
        if not device_id:
            raise ValueError("device_id cannot be empty")
        
        # Retry once if token is invalid
        for attempt in range(2):
            access_token = await self.get_access_token()
            
            url_path = PROPERTIES_URL.format(device_id=device_id)
            timestamp = self._get_timestamp()
            string_to_sign = (
                self._client_id + access_token + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + url_path
            )
            signed_string = self._get_sign(string_to_sign, self._client_secret)
            
            headers = {
                "client_id": self._client_id,
                "sign": signed_string,
                "access_token": access_token,
                "t": timestamp,
                "mode": "cors",
                "sign_method": "HMAC-SHA256",
                "Content-Type": "application/json",
            }
            
            url = self._base_url + url_path
            _, response_text = await self._make_request(url, method="GET", headers=headers)
            
            try:
                json_result = json.loads(response_text)
                
                # Check for token invalid error and retry with fresh token
                if self._is_token_invalid_error(json_result):
                    if attempt == 0:
                        # Calculate token age for detailed logging
                        token_age_hours = None
                        if self._token_expires_at:
                            token_age = (datetime.now() - (self._token_expires_at - timedelta(seconds=7200))).total_seconds()
                            token_age_hours = token_age / 3600
                        
                        _LOGGER.warning(
                            "ERROR 1010 (Token Invalid) detected in API call. "
                            "REASON: Tuya API access tokens expire after approximately 2 hours (7200 seconds). "
                            "Current token age: %s hours. "
                            "ACTION: Clearing cached token and requesting new token. "
                            "This is normal behavior and will be handled automatically.",
                            f"{token_age_hours:.2f}" if token_age_hours else "unknown"
                        )
                        self._clear_token()
                        continue
                    else:
                        error_msg = json_result.get("msg", "Unknown error")
                        error_code = json_result.get("code", "unknown")
                        _LOGGER.error(
                            "ERROR 1010 (Token Invalid) persists after token refresh attempt. "
                            "REASON: Token refresh may have failed or API credentials are invalid. "
                            "Check your API client_id and client_secret in integration settings."
                        )
                        raise ValueError(f"Tuya API error after token refresh: {error_msg} (code: {error_code})")
                
                # Check for other API errors
                if "success" in json_result and not json_result.get("success"):
                    error_msg = json_result.get("msg", "Unknown error")
                    error_code = json_result.get("code", "unknown")
                    raise ValueError(f"Tuya API error: {error_msg} (code: {error_code})")
                
                if "result" not in json_result:
                    raise ValueError(f"Invalid API response: {json_result}")
                
                result = json_result["result"]
                if "properties" not in result:
                    raise ValueError(f"Properties not found in response: {result}")
                
                properties = result["properties"]
                if not isinstance(properties, list):
                    raise ValueError(f"Expected list of properties, got: {type(properties)}")
                
                output = {prop.get("code"): prop.get("value") for prop in properties if "code" in prop}
                
                _LOGGER.debug("Retrieved %d properties for device %s", len(output), device_id)
                return output
                
            except json.JSONDecodeError as error:
                _LOGGER.error("Failed to parse device properties response: %s", error)
                raise ValueError(f"Invalid JSON response: {response_text}") from error

    async def get_device_model(self, device_id: str) -> Dict[str, Any]:
        """Get device model/schema for a specific device.
        
        Args:
            device_id: Tuya device ID.
            
        Returns:
            Dictionary containing the model response.
            
        Raises:
            aiohttp.ClientError: If API request fails.
            ValueError: If API response is invalid or device_id is empty.
        """
        if not device_id:
            raise ValueError("device_id cannot be empty")
        
        access_token = await self.get_access_token()
        
        url_path = MODEL_URL.format(device_id=device_id)
        timestamp = self._get_timestamp()
        string_to_sign = (
            self._client_id + access_token + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + url_path
        )
        signed_string = self._get_sign(string_to_sign, self._client_secret)
        
        headers = {
            "client_id": self._client_id,
            "sign": signed_string,
            "access_token": access_token,
            "t": timestamp,
            "mode": "cors",
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json",
        }
        
        url = self._base_url + url_path
        _, response_text = await self._make_request(url, method="GET", headers=headers)
        
        try:
            json_result = json.loads(response_text)
            if "result" not in json_result:
                raise ValueError(f"Invalid API response: {json_result}")
            
            return json_result
            
        except json.JSONDecodeError as error:
            _LOGGER.error("Failed to parse device model response: %s", error)
            raise ValueError(f"Invalid JSON response: {response_text}") from error

    def _extract_property_scales(self, model_response: Dict[str, Any]) -> Dict[str, int]:
        """Extract scale information for each property from the model response.
        
        Args:
            model_response: The response from get_device_model.
            
        Returns:
            Dictionary mapping property codes to their scale values.
            Example: {"temp_current": 1, "humidity_value": 0}
        """
        scales: Dict[str, int] = {}
        try:
            if "result" in model_response and "model" in model_response["result"]:
                model_str = model_response["result"]["model"]
                model_data = json.loads(model_str)
                
                # Look for properties in services
                if "services" in model_data:
                    for service in model_data["services"]:
                        # Check properties in service
                        if "properties" in service:
                            for prop in service["properties"]:
                                code = prop.get("code")
                                type_spec = prop.get("typeSpec", {})
                                scale = type_spec.get("scale")
                                if code and scale is not None:
                                    scales[code] = scale
                                    _LOGGER.debug("Found scale for %s: %s", code, scale)
        except Exception as e:
            _LOGGER.error("Error extracting scales from model: %s", e)
        
        return scales

    def get_cached_property_scale(self, device_id: str, property_code: str) -> Optional[int]:
        """Get the cached scale for a specific property (synchronous).
        
        This method only returns cached scales. Scales should be fetched
        during coordinator updates using get_device_model and _extract_property_scales.
        
        Args:
            device_id: Tuya device ID.
            property_code: Property code (e.g., "temp_current").
            
        Returns:
            Scale value (e.g., 1 means divide by 10, 0 means no scaling), or None if not found.
        """
        if device_id in self._property_scales:
            return self._property_scales[device_id].get(property_code)
        return None

    async def get_property_scale(self, device_id: str, property_code: str) -> Optional[int]:
        """Get the scale for a specific property, with caching.
        
        Args:
            device_id: Tuya device ID.
            property_code: Property code (e.g., "temp_current").
            
        Returns:
            Scale value (e.g., 1 means divide by 10, 0 means no scaling), or None if not found.
        """
        # Check cache first
        if device_id in self._property_scales:
            return self._property_scales[device_id].get(property_code)
        
        # Fetch model and extract scales
        try:
            model_response = await self.get_device_model(device_id)
            scales = self._extract_property_scales(model_response)
            self._property_scales[device_id] = scales
            _LOGGER.debug("Cached scales for device %s: %s", device_id, scales)
            return scales.get(property_code)
        except Exception as e:
            _LOGGER.warning("Failed to get scale for device %s property %s: %s", device_id, property_code, e)
            return None
        
        # Should never reach here, but just in case
        raise ValueError("Failed to get device properties after retry")
