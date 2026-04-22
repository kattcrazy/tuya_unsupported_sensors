"""Typed exceptions for Tuya Unsupported Sensors integration."""


class TuyaIntegrationError(Exception):
    """Base integration exception."""


class TuyaConnectionError(TuyaIntegrationError):
    """Error communicating with Tuya API."""


class TuyaAuthError(TuyaIntegrationError):
    """Authentication or token related failure."""


class TuyaDataError(TuyaIntegrationError):
    """Unexpected or malformed data from Tuya API."""


class TuyaDiscoveryError(TuyaIntegrationError):
    """Device discovery failure."""


class TuyaDatacenterMismatchError(TuyaDiscoveryError):
    """Configured region does not match account datacenter."""


class TuyaSubscriptionExpiredError(TuyaDiscoveryError):
    """Tuya cloud subscription/permission expired."""
