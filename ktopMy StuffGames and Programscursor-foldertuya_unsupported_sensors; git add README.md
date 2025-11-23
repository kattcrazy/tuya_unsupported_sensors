[1mdiff --git a/README.md b/README.md[m
[1mindex 8653223..23f85e5 100644[m
[1m--- a/README.md[m
[1m+++ b/README.md[m
[36m@@ -32,10 +32,12 @@[m [mFollow [this guide](https://github.com/azerty9971/xtend_tuya/blob/v4.2.4/docs/cl[m
 [m
 ### Troubleshooting[m
 **Trouble finding devices/incorrect API key:** Has your API key expired? Have you followed the steps above?[m
[32m+[m
 **Trouble finding devices:** Do you have devices to add? Have you followed the steps above?[m
[31m-**No entities in a device:** Check the list of supported sensors. If a sensor in the list doesn't work, go to https://us.platform.tuya.com/cloud/explorer > device control > Query properties and input your device's ID there (found https://platform.tuya.com/ > cloud > project management > open project > devices ) and paste the debugging response into a issue so I can add it.[m
[31m-**Error 1010 (Token Invalid):** Tuya API access tokens expire after approximately 2 hours, and the integration automatically refreshes tokens when this happens. If the issue persists, verify your API credentials are correct and create an issue containing your logs.[m
 [m
[32m+[m[32m**No entities in a device/unsupported:** Check the list of supported sensors. If a sensor in the list doesn't work, go to https://us.platform.tuya.com/cloud/explorer > device control > Query properties and input your device's ID there (found https://platform.tuya.com/ > cloud > project management > open project > devices ) and paste the debugging response into a issue so I can add it.[m
[32m+[m
[32m+[m[32m**Error 1010 (Token Invalid):** Tuya API access tokens expire after approximately 2 hours, and the integration automatically refreshes tokens when this happens. If the issue persists, verify your API credentials are correct and create an issue containing your logs.[m
 [m
 ## About[m
 This is my first ever github repo and my first time making a homeassistant intergration. I have tested it on my own setup and it works perfectly! Please report an issue if something doesn't work, I'll try my best to fix it.[m
