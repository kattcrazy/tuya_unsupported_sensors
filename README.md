# Overview
An intergration that creates devices & entites for sensors otherwise unsupported by the main tuya intergration.

## Sensors/entities supported
- Temperature
- Humidity
- Battery
- Door/contact

## Will not support
- Anything not listed above
- Anything that requires control will not be added, this is for read-only sensors

## Installation
- Download the folder named tuya_unsupported_sensors inside custom_components and drag/upload it into your custom_components folder inside your homeassistant configuration folder- for homeassistant docker custom_components is inside the folder that holds your configuration.yaml.
- Then go to settings > devices & intergrations > add intergration and search for Tuya Unsupported Sensors
- Fill in the required details (see Tuya dev api below) and choose a refresh interval.
- Then select your usually unsupported sensors from the list.

## Tuya Dev API
- View xxx link until step 5 to see how to set up the api credentials

## Troubleshooting
- Has your API expired?
- Have you connected it to your app?
- Do you have devices to add?
- No entities- check the list of supported sensors

## About
- This is my first ever github repo and my first time making a homeassistant intergration.
- I used Cursor AI to assist me with coding but the idea and implementation/plan/layout is mine.
- I have tested it on my own setup and it works perfectly! Please report an issue if something doesn't work :)