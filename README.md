# Tuya Unsupported Sensors

Home Assistant integration for connecting Tuya sensors/devices that aren't supported by the official Tuya integration.

## Installation (Docker)

1. Copy the `custom_components/tuya_unsupported_sensors` folder into your Home Assistant `custom_components` directory:
   ```bash
   docker cp tuya_unsupported_sensors <container_name>:/config/custom_components/
   ```

2. Restart Home Assistant

3. Go to **Settings → Devices & Services → Add Integration** and search for "Tuya Unsupported Sensors"

## Configuration

1. Select your Tuya region (US, EU, CN, etc.)
2. Enter your Tuya API credentials (Client ID and Client Secret)
3. Select which devices to integrate from the discovered list
4. Set update interval (1-30 minutes, default: 5 minutes)

## Requirements

- Tuya Cloud API credentials (Client ID and Client Secret)
- **Active Tuya developer trial or subscription** (expired trials will cause discovery failures)
- Home Assistant 2024.1.0 or later

## Troubleshooting

**Discovery Failed Error:**
- Verify your Tuya developer trial/subscription is active
- Check that your Client ID and Client Secret are correct
- Ensure you've selected the correct region (Western America = US, Eastern America = US East, etc.)
- Check Home Assistant logs for detailed error messages
