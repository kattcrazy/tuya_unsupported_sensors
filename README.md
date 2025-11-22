# Tuya Unsupported Sensors

An intergration that creates devices & entites for sensors otherwise unsupported by the main tuya/smart life intergration.

### Supported sensors/entities 
- Temperature
- Humidity
- Battery
- Door/contact

### Unsupported
- Anything that requires control (e.g: lights) will not be added, this is for read-only sensors
- If you have a read-only sensor you'd like to see you can submit an feature  request in the issues tab


## Installation (HACS) 
1. <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=kattcrazy&category=intergration&repository=tuya_unsupported_sensors" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>
2. Press download and restart Home Assistant.
3. Go to `Settings > Devices & Integrations > Add Integration` and search for Tuya Unsupported Sensors.
4. Fill in the required details (see Tuya Dev API below) and choose a refresh interval.
5. Select your usually unsupported sensors from the list.

## Installation (manual)
1. Download the folder named `tuya_unsupported_sensors` inside `custom_components`
2. Drag/upload it into your `custom_components` folder inside your Home Assistant configuration folder (for Home Assistant Docker, `custom_components` is inside the folder that holds your `configuration.yaml`).
3. Go to `Settings > Devices & Integrations > Add Integration` and search for Tuya Unsupported Sensors.
4. Fill in the required details (see Tuya Dev API below) and choose a refresh interval.
5. Select your usually unsupported sensors from the list.

## Tuya Dev API
Follow [this guide](https://github.com/azerty9971/xtend_tuya/blob/v4.2.4/docs/cloud_credentials.md) until step 5 to see how to set up the API credentials (credit [@azerty9971](https://github.com/azerty9971)).

### Troubleshooting
**Trouble finding devices/incorrect API key:** Has your API key expired? Have you followed the steps above?
**Trouble finding devices:** Do you have devices to add? Have you followed the steps above?
**No entities in a device:** Check the list of supported sensors. If a sensor in the list doesn't work, go to https://us.platform.tuya.com/cloud/explorer > device control > Query properties and input your device's ID there (found https://platform.tuya.com/ > cloud > project management > open project > devices ) and paste the debugging response into a issue so I can add it.
**Error 1010 (Token Invalid):** Tuya API access tokens expire after approximately 2 hours, and the integration automatically refreshes tokens when this happens. If the issue persists, verify your API credentials are correct and create an issue containing your logs.


## About
This is my first ever github repo and my first time making a homeassistant intergration. I have tested it on my own setup and it works perfectly! Please report an issue if something doesn't work, I'll try my best to fix it.

Support me [here](https://summersketches.com/product/support-me/)