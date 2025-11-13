# Tuya Unsupported Sensors

## Overview
An intergration that creates devices & entites for sensors otherwise unsupported by the main tuya/smart life intergration.

## Sensors/entities supported
- Temperature
- Humidity
- Battery
- Door/contact

## Will not support
- Anything not listed above
- Anything that requires control (e.g: lights) will not be added, this is for read-only sensors

## Installation (manual)
1. Download the folder named `tuya_unsupported_sensors` inside `custom_components`
2. Drag/upload it into your `custom_components` folder inside your Home Assistant configuration folder (for Home Assistant Docker, `custom_components` is inside the folder that holds your `configuration.yaml`).
3. Go to `Settings > Devices & Integrations > Add Integration` and search for **Tuya Unsupported Sensors**.
4. Fill in the required details (see Tuya Dev API below) and choose a refresh interval.
5. Select your usually unsupported sensors from the list.

## Installation (HACS) 
1. In Home Assistant, open **HACS** and choose **Integrations**.
2. Click the three-dot menu and pick **Custom repositories**.
3. Enter `https://github.com/kattcrazy/tuya_unsupported_sensors` as the repository URL and choose **Integration** as the category and click **Add**.
5. Return to the HACS Integrations page, search for **Tuya Unsupported Sensors**, and download it.
6. Restart Home Assistant
7. Go to `Settings > Devices & Integrations > Add Integration` and search for **Tuya Unsupported Sensors**.
3. Fill in the required details (see Tuya Dev API below) and choose a refresh interval.
4. Select your usually unsupported sensors from the list.

## Tuya Dev API
- Follow [this guide](https://github.com/azerty9971/xtend_tuya/blob/v4.2.4/docs/cloud_credentials.md) until step 5 to see how to set up the API credentials (credit @azerty9971)

## Troubleshooting
- Trouble finding devices/incorrect API key: Has your API expired?
- Trouble finding devices/incorrect API key: Have you connected it to your app?
- Trouble finding devices: Do you have devices to add?
- No entities in a device: Check the list of supported sensors

## About
This is my first ever github repo and my first time making a homeassistant intergration. I have tested it on my own setup and it works perfectly! Please report an issue if something doesn't work :)
Support me [here](https://summersketches.com/product/support-me/): 