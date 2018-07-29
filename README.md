# RFPlayer

Plugin for the Indigo Home Automation system.

This plugin communicates with the ZiBlue RFPLayer RF multiprotocol USB dongle.  The RFPlayer supports transmit and receive commands on the 433MHz and 866MHz bands (EU) or 310/315MHz and 433MHz bands (US) .

Supported devices include:
	
* Visonic
* Domia/ARC
* X10
* Somfy RTS
* Blyss
* Oregon Scientific

"Parrot" mode supports sending or triggering on learned commands not associated with a specific device protocol.
	
See http://rfplayer.com/ for details.

## Quick Start

1. Connect the RFPlayer dongle to an available USB port
1. Install the RFPlayer plugin
1. Optionally set the plugin configuration information for temperature units and plugin update check frequency.
2. Create a new RFPlayer device of type "RFPlayer Dongle".  Select the serial port the dongle is connected to.  Select US or EU depending on your RFPlayer model (different frequency bands are used US vs EU).
3. The dongle will start listening for sensor transmissions on the default RF bands.  The plugin will collect information about each new sensor that transmissions are received from.
4. Create new RFPlayer devices for each sensor.  The known devices will be available in the popup list for Discovered Devices.



-

This plugin uses a local USB device.  Internet access not required except for plugin update checks.


**PluginID**: com.flyingdiver.indigoplugin.rfplayer

### Indigo 7 Only

This plugin requires Indigo 7 or greater.

