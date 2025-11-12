# Tuya Unsupported Sensors - Implementation Plan

## Project Overview

**Name:** Tuya Unsupported Sensors  
**Domain:** `tuya_unsupported_sensors`  
**Description:** "Allowing you to connect your Tuya sensors or devices that can't be connected via the official integration"

**Purpose:** Convert the existing Tuya API v3 script into a HACS integration for Home Assistant that allows users to connect unsupported Tuya devices (sensors only FOR NOW BUT WILL ADD CONTROL IN FUTURE).

---

## Requirements & Decisions

### Scope
- **Sensors only** (sensors only FOR NOW BUT WILL ADD CONTROL IN FUTURE)
- **Manual device selection** from auto-discovered list
- **Multi-region support** (US, EU, CN, IN, etc.)
- **Update interval:** User configurable between 1-30 minutes (default: 5 minutes)
- **Custom sensor names:** Users can customize sensor names

### Device Selection
- Auto-discover devices via Tuya API
- Show device name + ID in selection list
- Multi-select interface for choosing devices
- show ALL discovered devices and have a bit of text that says "We reccomend selecting only the devices that you can't connect via the main intergration"

### Region Support
Support all Tuya regions:
- **US (Western):** `https://openapi.tuyaus.com`
- **US (Eastern):** `https://openapi-ueaz.tuyaus.com`
- **EU (Central):** `https://openapi.tuyaeu.com`
- **EU (Western):** `https://openapi-weaz.tuyaeu.com`
- **China:** `https://openapi.tuyacn.com`
- **India:** `https://openapi.tuyain.com`
- **Singapore:** `https://openapi.tuyasg.com`
- **Japan:** `https://openapi.tuyajp.com`
- (Add more regions as needed or discovered)

---

## File Structure

```
TuyaUnsupportedDevices/
├── hacs.json                          # HACS manifest (root level)
├── README.md                          # User documentation
├── PLAN.md                            # This file - implementation plan
├── custom_components/
│   └── tuya_unsupported_sensors/
│       ├── __init__.py                # Integration entry point
│       ├── manifest.json              # Home Assistant manifest
│       ├── const.py                   # Constants (regions, endpoints, config keys)
│       ├── tuya_api.py                # API client (refactored from tuyav3 copy.py)
│       ├── config_flow.py             # Multi-step configuration UI
│       ├── coordinator.py             # Data update coordinator
│       ├── sensor.py                  # Sensor entities
│       ├── binary_sensor.py           # Binary sensor entities
│       ├── strings.json               # UI strings for config flow
│       ├── icon.svg                   # Integration icon (SVG)
│       └── icon.png                   # Integration icon (PNG)
└── tuyav3 copy.py                     # Original script (reference)
```

---

## Implementation Details

### 1. hacs.json (Root)
- **name:** "Tuya Unsupported Sensors"
- **content_in_root:** false (integration is in custom_components/)
- **homeassistant:** "2024.1.0" (minimum required version)
- **hacs:** "1.0.0" (minimum required HACS version)
- ✅ **COMPLETED**

### 2. manifest.json (Integration)
Required fields:
- **domain:** `tuya_unsupported_sensors`
- **name:** "Tuya Unsupported Sensors"
- **version:** "1.0.0" (initial)
- **codeowners:** @YoungsRTheBest
- **documentation:** GitHub repo URL
- **issue_tracker:** GitHub issues URL
- **config_flow:** true
- **iot_class:** "cloud_polling"
- **integration_type:** "hub"
- **brand:** "tuya_unsupported_sensors" (for icon support)
- ✅ **COMPLETED**

### 3. const.py
Constants needed:
- `DOMAIN = "tuya_unsupported_sensors"`
- Region mappings dictionary:
  ```python
  REGIONS = {
      "us": "https://openapi.tuyaus.com",           # US Western
      "us_east": "https://openapi-ueaz.tuyaus.com", # US Eastern
      "eu": "https://openapi.tuyaeu.com",           # EU Central
      "eu_west": "https://openapi-weaz.tuyaeu.com", # EU Western
      "cn": "https://openapi.tuyacn.com",           # China
      "in": "https://openapi.tuyain.com",           # India
      "sg": "https://openapi.tuyasg.com",           # Singapore
      "jp": "https://openapi.tuyajp.com",           # Japan
  }
  ```
- API endpoints:
  - `LOGIN_URL = "/v1.0/token?grant_type=1"`
  - `DEVICE_LIST_URL = "/v2.0/cloud/thing/device"` (with pagination support: `page_size`, `last_id`)
  - `PROPERTIES_URL = "/v2.0/cloud/thing/{device_id}/shadow/properties"`
- `EMPTY_BODY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"`
- Configuration keys:
  - `CONF_CLIENT_ID`
  - `CONF_CLIENT_SECRET`
  - `CONF_REGION`
  - `CONF_DEVICES` (list of device IDs)
  - `CONF_UPDATE_INTERVAL` (minutes, 1-30)
- Sensor type mappings (temperature, humidity, battery, contact, motion, etc.)

### 4. tuya_api.py
Refactor from `tuyav3 copy.py`:

**TuyaAPIClient class:**
- `__init__(client_id, client_secret, region)` - Initialize with credentials and region
- `get_access_token()` - Get/refresh access token (cache token, check expiry)
- `discover_devices()` - List all devices from user account
- `get_device_properties(device_id)` - Get device properties/sensor values
- `make_request(url, method="GET", params=None, headers=None, body=None)` - Generic HTTP request handler
- `get_sign(payload, key)` - HMAC-SHA256 signature generation
- `get_timestamp()` - Timestamp generation

**Features:**
- Token caching and automatic refresh
- Region-aware base URL selection
- Error handling and retry logic
- Rate limit awareness (500k/day, 500/sec)

### 5. config_flow.py
Multi-step configuration flow:

**Step 1: Region Selection**
- Dropdown: US, EU, CN, IN, etc.
- Store: `CONF_REGION`

**Step 2: Credentials**
- Input: Client ID (`CONF_CLIENT_ID`)
- Input: Client Secret (`CONF_CLIENT_SECRET`)
- Password field for secret

**Step 3: Validate Credentials**
- Test API connection
- Show error if invalid
- On success, proceed to device discovery

**Step 4: Discover Devices**
- Call `discover_devices()` API
- Show loading state
- Handle errors

**Step 5: Device Selection**
- Multi-select list showing: "Device Name (device_id)"
- Show ALL discovered devices
- Add informational text: "We recommend selecting only the devices that you can't connect via the main integration"
- Store selected device IDs: `CONF_DEVICES` (list)

**Step 6: Update Interval**
- Number input: 1-30 minutes
- Default: 5 minutes
- Store: `CONF_UPDATE_INTERVAL`

**Step 7: Confirm**
- Review selections
- Create config entry

**Additional:**
- Options flow for reconfiguration
- Import flow (optional, for YAML config)

### 6. coordinator.py
**ExtraTuyaSensorsDataUpdateCoordinator class:**
- Extends `DataUpdateCoordinator`
- Periodic updates based on user-configured interval (1-30 minutes)
- Token refresh handling
- Update all selected devices' properties
- Error handling and retry logic
- Rate limit awareness
- Notify listeners when data updates

**Update method:**
- For each device in config:
  - Call `get_device_properties(device_id)`
  - Store results in coordinator data
  - Handle errors gracefully

### 7. sensor.py
**Platform setup:**
- `async_setup_entry(hass, config_entry, async_add_entities)`
- Create sensor entities for each device property
- **IMPORTANT:** Register each Tuya device as a Device in Home Assistant's device registry
- Create entities that belong to their parent device

**Device Registration:**
- Use `async_get_device_registry()` to get device registry
- Create device entry with:
  - `identifiers`: `{(DOMAIN, device_id)}`
  - `name`: Device name from Tuya API (`customName` first, then `name`)
  - `manufacturer`: "Tuya"
  - `model`: Device model (`product_name` from API)
  - `via_device`: None (root device)
- Store device_id in entity's `device_info`
- Entity names use format: `{device_name} {friendly_property_name}`

**ExtraTuyaSensor class:**
- Extends `SensorEntity`
- **device_info property:** Returns device info linking entity to parent device:
  ```python
  @property
  def device_info(self):
      return {
          "identifiers": {(DOMAIN, self.device_id)},
          "name": self.device_name,
          "manufacturer": "Tuya",
          "model": self.device_model,
      }
  ```
- Dynamic sensor creation based on device properties:
  - Temperature sensors → `device_class: temperature`, `unit_of_measurement: °C` or `°F`
  - Humidity sensors → `device_class: humidity`, `unit_of_measurement: %`
  - Battery sensors → `device_class: battery`
    - **IMPORTANT:** Battery values may come as text (e.g., "high", "medium", "low") or as percentage (0-100)
    - Need to detect value type and handle accordingly:
      - If numeric (int/float): Use `unit_of_measurement: %`
      - If text: No unit, display text value as-is, or map to percentage if possible
      - Handle per entity based on actual value received
  - Generic property sensors for other values
- Custom name support (from config or default)
- State updates from coordinator
- Attributes (device_id, property_code, etc.)
- Entity ID format: `sensor.{device_name}_{property_code}` (e.g., `sensor.joels_office_temperature`)

### 8. binary_sensor.py
**Platform setup:**
- `async_setup_entry(hass, config_entry, async_add_entities)`
- Create binary sensor entities for binary properties
- **IMPORTANT:** Entities must belong to their parent device (same device_info pattern as sensor.py)

**ExtraTuyaBinarySensor class:**
- Extends `BinarySensorEntity`
- **device_info property:** Returns device info linking entity to parent device (same as sensor.py)
- Binary sensor types:
  - Contact sensors → `device_class: door` or `window`
  - Motion sensors → `device_class: motion`
  - Other boolean states from device properties
- Custom name support
- State updates from coordinator
- Attributes (device_id, property_code, etc.)
- Entity ID format: `binary_sensor.{device_name}_{property_code}` (e.g., `binary_sensor.sadies_food_bowl_contact`)

### 9. __init__.py
**Integration setup:**
- `DOMAIN` constant
- `async_setup(hass, config)` - Register integration
- `async_setup_entry(hass, entry)` - Set up config entry:
  - Initialize API client with credentials from config entry
  - Create coordinator with update interval from config
  - Set up platforms (sensor, binary_sensor)
  - Store coordinator and API client in hass.data[DOMAIN][entry.entry_id]
  - Register devices in device registry (one per device_id)
- `async_unload_entry(hass, entry)` - Cleanup on unload:
  - Unload platforms
  - Clean up coordinator
  - Remove from hass.data
- Config entry update listener (for options flow changes)

---

## Tuya API Details

### Authentication
- Method: HMAC-SHA256
- Endpoint: `/v1.0/token?grant_type=1`
- Headers required:
  - `client_id`
  - `sign` (HMAC-SHA256 signature)
  - `t` (timestamp in milliseconds)
  - `mode: cors`
  - `sign_method: HMAC-SHA256`
  - `Content-Type: application/json`

### Signature Generation
```
string_to_sign = client_id + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + URL_PATH
sign = HMAC-SHA256(string_to_sign, client_secret).hexdigest().upper()
```

### Device Discovery
- **Endpoint:** `/v1.0/devices` (primary endpoint)
- **Alternative:** `/v1.0/users/{uid}/devices` (if user-specific endpoint needed)
- **Method:** GET
- **Requires:** access_token in headers
- **Returns:** List of devices with:
  - `id` (device_id)
  - `name` (device name)
  - `product_id` (product identifier)
  - `product_name` (product name/model)
  - Other device metadata
- **Note:** May need to handle pagination if user has many devices

### Device Properties
- Endpoint: `/v2.0/cloud/thing/{device_id}/shadow/properties`
- Method: GET
- Requires: access_token
- Returns: Device properties (sensor values)

### Rate Limits
- Application layer: 500,000 requests/day
- Interface level: 500 requests/second
- Implement rate limiting awareness

---

## Device Property Mapping

### Sensor Types (Common Property Codes)
- `temp` or `temperature` or `va_temperature` → Temperature sensor (°C/°F)
- `humidity` or `va_humidity` → Humidity sensor (%)
- `battery` or `battery_percentage` or `battery_state` → Battery sensor (%) **NOTE BATTERY MAY BE IN TEXT NOT % IF SO WILL NEED TO ADJUST ACCORDINGLY PER ENTITY)
- `battery_value` → Battery voltage/value
- Other numeric properties → Generic sensor (preserve original property code)

### Binary Sensor Types (Common Property Codes)
- `contact` or `doorcontact_state` or `door_sensor_state` → Contact sensor (door/window)
  - Values: `true`/`false` or `1`/`0` or `"open"`/`"close"`
- `motion` or `pir` or `pir_state` → Motion sensor
  - Values: `true`/`false` or `1`/`0` or `"pir"`/`"none"`
- `online` → Device online status
- Other boolean properties → Generic binary sensor

### Property Value Handling
- Properties come from API as: `{"code": "property_code", "value": <value>}`
- Need to handle different value types:
  - Numbers (int/float) → Sensor entities
  - Booleans/strings → Binary sensor entities (map to on/off)
  - Strings like "open"/"close" → Map to binary states
- **Battery Value Handling:**
  - Battery values may be numeric (percentage 0-100) OR text (e.g., "high", "medium", "low")
  - Implementation uses dynamic `device_class` property:
    - If numeric: Sets `device_class: BATTERY`, `unit_of_measurement: %`, `state_class: MEASUREMENT`
    - If text: Sets `device_class: None`, `unit_of_measurement: None`, `state_class: None`
    - Prevents Home Assistant from trying to convert text values to float
- **Temperature Value Handling:**
  - Tuya API returns temperature scaled by 10 (e.g., 217 = 21.7°C, 700 = 70°F)
  - Implementation divides by 10 if temperature > 100
  - Unit detection: Checks `temp_unit_convert` property ("c" or "f") to set correct unit
- **Entity Naming:**
  - Uses friendly name mapping: Battery State → Battery, Humidity Value → Humidity, etc.
  - Device names use Tuya `customName` first, then `name` (not generic device types)

---

## Implementation Order

1. ✅ Create file structure with comments
2. ✅ Create `const.py` with all constants
2.1. ✅ Create `hacs.json` (root level HACS manifest)
3. ✅ Refactor `tuya_api.py` from `tuyav3 copy.py`
4. ✅ Create `manifest.json` (integration manifest)
5. ✅ Create `config_flow.py` (multi-step)
6. ✅ Create `coordinator.py`
7. ✅ Create `sensor.py` and `binary_sensor.py`
8. ✅ Create `__init__.py` to tie everything together
9. ✅ Create `README.md` with documentation
10. ⏳ Test integration (IN PROGRESS)
11. ⏳ Refine and fix issues (PENDING TESTING)

---

## Testing Checklist

- [ ] Config flow works (all steps)
- [ ] Credential validation works
- [ ] Device discovery works
- [ ] Device selection saves correctly
- [ ] Update interval is respected
- [ ] **Devices are registered in device registry**
- [ ] **Entities are properly linked to their parent devices**
- [ ] Sensors update correctly
- [ ] Binary sensors update correctly
- [ ] Token refresh works
- [ ] Error handling works (invalid credentials, API errors, etc.)
- [ ] Multiple regions work
- [ ] Multiple devices work
- [ ] Custom sensor names work
- [ ] **Battery sensors handle both numeric and text values correctly**
- [ ] Integration unloads cleanly
- [ ] Options flow works (reconfiguration)

---

## Notes

- Original script: `tuyav3 copy.py` (reference for API implementation)
- Remove hardcoded credentials from API client
- Use Home Assistant's async/await patterns
- Follow Home Assistant integration best practices
- Handle edge cases (no devices, API errors, etc.)
- Add proper logging
- Consider rate limiting implementation

---

## Resources

- HACS Documentation: https://www.hacs.xyz/docs/publish/integration/
- Home Assistant Integration Documentation: https://developers.home-assistant.io/docs/creating_integration_manifest/
- Tuya API Documentation: https://developer.tuya.com/en/docs/cloud/
- Home Assistant Config Flow: https://developers.home-assistant.io/docs/config_entries_config_flow_handler/

---

## Resolved Questions

### 1. Device Discovery Endpoint
- **Primary endpoint:** `/v2.0/cloud/thing/device` (GET)
- **Required parameter:** `page_size` (max 20, required)
- **Pagination:** Uses `last_id` parameter to fetch next page
- Returns list of all devices associated with the API credentials
- Response includes device ID, name (`customName` or `name`), product info
- Normalizes device names: Uses `customName` first, then `name` as fallback

### 2. Token Expiry & Refresh
- **Token lifetime:** Typically 2 hours (7200 seconds)
- **Refresh:** Use same `/v1.0/token?grant_type=1` endpoint to get new token
- **Implementation:** Check token expiry before API calls, refresh proactively
- Store `expires_at` timestamp and refresh when < 5 minutes remaining
- No separate refresh token needed - use same grant_type=1 flow

### 3. Device Property Codes
- Common codes documented in "Device Property Mapping" section above
- Properties come from `/v2.0/cloud/thing/{device_id}/shadow/properties`
- Response format: `{"result": {"properties": [{"code": "...", "value": ...}]}}`
- Property codes vary by device type/product
- Need to dynamically detect property types (numeric vs boolean/string)

### 4. Binary Sensor State Mapping
- Contact sensors: May report as `true`/`false`, `1`/`0`, or `"open"`/`"close"`
- Motion sensors: May report as `true`/`false`, `1`/`0`, or `"pir"`/`"none"`
- **Implementation:** Create mapping function to normalize values:
  - `true`, `1`, `"open"`, `"pir"` → `ON` state
  - `false`, `0`, `"close"`, `"none"` → `OFF` state
  - Handle edge cases and unknown values gracefully

---

## Placeholders That Need to Be Updated

1. **GitHub Repository URLs** (in `manifest.json`):
   - `"documentation": "https://github.com/YoungsRTheBest/tuya_sensors_plus"`
   - `"issue_tracker": "https://github.com/YoungsRTheBest/tuya_sensors_plus/issues"`
   - **Action Required:** Update these URLs once the actual GitHub repository is created

2. **Codeowner** (in `manifest.json`):
   - `"codeowners": ["@YoungsRTheBest"]`
   - **Note:** Verify this GitHub username is correct before publishing

---

## Implementation Accomplishments

### Core Integration Files ✅
- ✅ **File Structure:** Created complete HACS integration structure in `custom_components/tuya_unsupported_sensors/`
- ✅ **hacs.json:** Root-level HACS manifest with correct metadata
- ✅ **manifest.json:** Home Assistant integration manifest with all required fields (including brand for icon support)
- ✅ **const.py:** Centralized constants including regions, endpoints, property codes, and configuration keys
- ✅ **strings.json:** UI strings for config flow and error messages
- ✅ **icon.svg & icon.png:** Integration icons (requires submission to Home Assistant brands repository)

### API Client ✅
- ✅ **tuya_api.py:** Fully refactored from original script into async class-based API client
  - HMAC-SHA256 authentication implementation
  - Token caching and automatic refresh logic
  - Multi-region support (US, EU, CN, IN, SG, JP with East/West variants)
  - Device discovery endpoint integration
  - Device properties fetching
  - Comprehensive error handling

### Configuration Flow ✅
- ✅ **config_flow.py:** Complete multi-step configuration UI
  - Step 1: Region selection (8 regions supported)
  - Step 2: Credentials input with validation
  - Step 3: Device discovery with loading states
  - Step 4: Multi-select device selection with smart filtering
    - Prioritizes unadded devices (not in other Tuya integrations)
    - Marks already-added devices with indicator
    - Only checks devices from enabled Tuya config entries
    - Excludes disabled devices (disabled_by check)
    - Excludes unsupported devices (no active entities check)
    - Only matches by device ID (not name) to avoid false positives
  - Step 5: Update interval configuration (1-30 minutes, number input)
  - Options flow for reconfiguration
  - Proper error handling (InvalidAuth, CannotConnect)
  - Uses Tuya customName for device names (not generic device types)

### Data Management ✅
- ✅ **coordinator.py:** DataUpdateCoordinator implementation
  - Periodic updates based on user-configured interval
  - Handles multiple devices simultaneously
  - Individual device error handling
  - Token refresh integration

### Entity Platforms ✅
- ✅ **sensor.py:** Dynamic sensor entity creation
  - Temperature, humidity, battery sensors with proper device classes
  - Temperature scaling: Divides by 10 if value > 100 (Tuya API returns scaled values, e.g., 217 = 21.7°C)
  - Fahrenheit support: Detects `temp_unit_convert` property and sets unit accordingly
  - Battery value handling: Dynamic device_class property - only sets BATTERY class if value is numeric
    - Text battery values (e.g., "middle", "high", "low") display as text sensors without device_class
    - Prevents Home Assistant from trying to convert text to float
  - Friendly entity names: Battery State → Battery, Humidity Value → Humidity, Temperature Current → Temperature
  - Dynamic unit of measurement assignment
  - State class handling (only for numeric values)
  - Device registry integration
  - Uses Tuya customName for entity names

- ✅ **binary_sensor.py:** Dynamic binary sensor entity creation
  - Contact, motion, online sensors with proper device classes
  - Friendly entity names: Doorcontact State → Contact
  - Value normalization (handles true/false, 1/0, "open"/"close", "pir"/"none")
  - Raw value preservation in attributes for debugging
  - Device registry integration
  - Uses Tuya customName for entity names

### Integration Setup ✅
- ✅ **__init__.py:** Complete integration orchestration
  - Domain registration
  - Config entry setup and teardown
  - API client initialization
  - Coordinator setup
  - Device registry registration (uses Tuya customName)
  - Platform forwarding
  - Options update listener

### Documentation ✅
- ✅ **README.md:** User-facing documentation
  - Docker-specific installation instructions
  - Configuration walkthrough
  - Requirements listed

- ✅ **PLAN.md:** Comprehensive implementation plan and documentation
- ✅ **TESTING_CHECKLIST.md:** Detailed testing checklist for validation phase

### Code Quality ✅
- ✅ Code review completed
  - Removed redundant imports
  - Fixed incorrect callback decorators
  - Improved battery sensor logic
  - Concise comments (only where needed)
  - Consistent naming conventions
  - Proper async/await patterns throughout

### Cleanup ✅
- ✅ Removed old `extra_tuya_sensors` and `tuya_sensors_plus` folders after rename to `tuya_unsupported_sensors`
- ✅ Identified and documented placeholders (GitHub URLs in manifest.json)

---

## Recent Updates

- ✅ **RENAMED:** Integration renamed from "Tuya Sensors Plus" to "Tuya Unsupported Sensors" (domain: `tuya_unsupported_sensors`)
- ✅ Updated scope to note future control support
- ✅ Changed default update interval to 5 minutes (number input, not slider)
- ✅ Set codeowner to @YoungsRTheBest
- ✅ Added device selection recommendation text
- ✅ Expanded region support to include all Tuya regions (US East/West, EU Central/West, CN, IN, SG, JP)
- ✅ **MAJOR:** Changed entity structure to use Home Assistant Device Registry
  - Each Tuya device is registered as a Device
  - Sensor/binary sensor entities are nested under their parent device
  - Entities use `device_info` property to link to parent device
- ✅ Resolved API endpoint questions (device discovery uses `/v2.0/cloud/thing/device` with pagination)
- ✅ Added property value normalization for binary sensors
- ✅ **Battery value handling:** Dynamic device_class property - only sets BATTERY class for numeric values
  - Text battery values display as text sensors without device_class
  - Prevents Home Assistant conversion errors
- ✅ **Temperature scaling:** Fixed to divide by 10 if temperature > 100 (handles Tuya API scaling)
- ✅ **Fahrenheit support:** Detects `temp_unit_convert` property and sets unit accordingly
- ✅ **Friendly entity names:** Added name mapping (Battery State → Battery, etc.)
- ✅ **Device filtering improvements:**
  - Only checks devices from enabled Tuya config entries
  - Excludes disabled devices (checks `disabled_by`)
  - Excludes unsupported devices (checks for active entities)
  - Only matches by device ID (not name) to avoid false positives with non-Tuya devices
- ✅ **Device naming:** Uses Tuya `customName` first, then `name` for all device and entity names
- ✅ **Entity ID formatting:** Entity IDs now use slugified custom names and friendly property names (e.g., "Joel's Office" + "Battery" → "joel_s_office_battery")
- ✅ Code review completed - removed redundant imports, fixed callback decorators, improved battery sensor logic
- ✅ Added icon support (icon.svg and icon.png) - requires submission to Home Assistant brands repository
- ✅ Created comprehensive testing checklist
- ✅ Updated PLAN.md with full implementation accomplishments
- ✅ Added configuration flow guidance link to Xtend Tuya cloud credential guide (steps 1–5) on the credentials page
- ✅ Updated `manifest.json` documentation and issue tracker URLs to final repository name (`tuya_unsupported_sensors`)
- ✅ Updated `manifest.json` code owners and URLs to new GitHub username (`@Kattcrazy`)

---

## Current Status

**Phase:** 🧪 Testing & Refinement Phase  
**Completion:** ~98% (Core implementation complete, testing and bug fixes in progress)

**Recent Fixes:**
- ✅ Fixed temperature scaling (217 → 21.7°C)
- ✅ Fixed battery text value handling (dynamic device_class property)
- ✅ Added Fahrenheit support
- ✅ Added friendly entity names
- ✅ Fixed device filtering to exclude disabled/unsupported devices
- ✅ Fixed device name matching to use Tuya customName
- ✅ Fixed false positives from non-Tuya devices (only matches by device ID)
- ✅ Updated entity IDs to use slugified custom names instead of device IDs

**Next Steps:**
1. Complete testing and validation
2. Submit icon to Home Assistant brands repository
3. Update GitHub repository URLs in manifest.json
4. Prepare for HACS submission

---

**Last Updated:** 9:04am 13/11/2025

## HACS Submission Prep (Pre-GitHub)

- Repository prep
  - Set GitHub repo to public, add concise description and topics (per HACS publish requirements)
  - Ensure `hacs.json` remains in root and reflects integration name/version
  - Verify `manifest.json` documentation/issue tracker URLs after repo is created
- Release process
  - Create semantic versioned GitHub release (tags + release notes) when ready
  - Include the `custom_components/tuya_unsupported_sensors` folder in release assets if using zip
- Branding
  - Submit `icon.svg`/`icon.png` to Home Assistant brands repo (`https://github.com/home-assistant/brands`)
  - Use same domain (`tuya_unsupported_sensors`) in `manifest.json` and brand submission
- Documentation
  - Update `README.md` with installation/config steps and My Home Assistant link if desired
  - Add HACS My link (`https://my.home-assistant.io/create-link/?redirect=hacs_repository`) after repo exists
- Testing
  - Confirm config flow works from clean setup
  - Run through discovery with renewed Tuya credentials before tagging release

