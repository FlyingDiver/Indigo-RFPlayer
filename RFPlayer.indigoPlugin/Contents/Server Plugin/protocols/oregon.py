#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo


class Oregon(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        devAddress = "OREGON-" + frameData['infos']['adr_channel']
        if devAddress not in knownDevices:
            indigo.server.log(f"New device added to Known Device list: {devAddress}")
            knownDevices[devAddress] = {
                "status": "Available",
                "devices": indigo.List(),
                "protocol": frameData['header']['protocol'],
                "description": frameData['infos']['id_PHYMeaning'],
                "subType": frameData['infos']['id_PHY'],
                "playerId": playerDevice.id,
                "frameData": frameData
            }
        else:
            knownDevices[devAddress]["playerId"] = playerDevice.id
        return devAddress

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.Oregon")
        self.device = device
        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(f"{device.name}: Starting Oregon Scientific device ({subType}) @ {devAddress}")
        self.player = indigo.devices[knownDevices[devAddress]['playerId']]

        configDone = device.pluginProps.get('configDone', False)
        self.logger.threaddebug(f"{device.name}: __init__ configDone = {str(configDone)}")
        if configDone:
            return

        knownDevices.setitem_in_item(devAddress, 'status', "Active")
        devices = knownDevices[devAddress]['devices']
        devices.append(device.id)
        knownDevices.setitem_in_item(devAddress, 'devices', devices)

        # update the master device, depending on the actual device type 

        if subType not in ['0x1A89', '0x2A19', '0xDA78']:

            device.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)
            device.subModel = "Thermometer"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "temperature"
            newProps["SupportsBatteryLevel"] = True
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(f"Configured Oregon Scientific Temperature Sensor '{device.name}' ({device.id}) @ {devAddress}")

        elif subType == '0x1A89':  # Wind Sensor

            device.updateStateImageOnServer(indigo.kStateImageSel.WindSpeedSensor)
            device.subModel = "Wind Speed"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "speed"
            newProps["SupportsBatteryLevel"] = True
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(f"Configured Oregon Scientific Wind Sensor '{device.name}' ({device.id}) @ {devAddress}")

        elif subType == '0x2A19':  # Rain Sensor

            device.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensor)
            device.subModel = "Rain Sensor"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "rain"
            newProps["SupportsBatteryLevel"] = True
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(f"Configured Oregon Scientific Rain Sensor '{device.name}' ({device.id}) @ {devAddress}")

        elif subType == '0xDA78':  # UV Sensor

            device.updateStateImageOnServer(indigo.kStateImageSel.LightSensor)
            device.subModel = "UV Sensor"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "uv"
            newProps["SupportsBatteryLevel"] = True
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(f"Configured Oregon Scientific UV Sensor '{device.name}' ({device.id}) @ {devAddress}")

        else:
            self.logger.error(f"{subType}: Unknown Device Type = {subType}")
            return

        # create any sub-devices

        if subType in ['0x1A2D', '0xCA2C', '0x0ACC', '0x1A3D', '0xFA28']:

            self.logger.info(f"Adding Hygrometer subDevice to '{device.name}' ({device.id}) @ {devAddress}")

            newdev = indigo.device.create(indigo.kProtocol.Plugin,
                                          address=devAddress,
                                          name=device.name + " Hygrometer",
                                          deviceTypeId="discoveredDevice",
                                          groupWithDevice=device.id,
                                          props={'valueType': 'hygrometry',
                                                 'configDone': True,
                                                 'AllowOnStateChange': False,
                                                 'SupportsOnState': False,
                                                 'SupportsSensorValue': True,
                                                 'SupportsStatusRequest': False
                                                 },
                                          folder=device.folderId)

            newdev.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensor)
            newdev.model = device.model
            newdev.subModel = "Hygrometer"  # Manually need to set the model and subModel names (for UI only)
            newdev.replaceOnServer()

            devices = knownDevices[devAddress]['devices']
            devices.append(newdev.id)
            knownDevices.setitem_in_item(devAddress, 'devices', devices)
            knownDevices.setitem_in_item(devAddress, 'status', "Active")

        elif subType == '0x5A6D':

            self.logger.info(f"Adding Barometer subDevice to '{device.name}' ({device.id}) @ {devAddress}")

            newdev = indigo.device.create(indigo.kProtocol.Plugin,
                                          address=devAddress,
                                          name=device.name + " Barometer",
                                          deviceTypeId="discoveredDevice",
                                          groupWithDevice=device.id,
                                          props={'valueType': 'pressure',
                                                 'configDone': True,
                                                 'AllowOnStateChange': False,
                                                 'SupportsOnState': False,
                                                 'SupportsSensorValue': True,
                                                 'SupportsStatusRequest': False
                                                 },
                                          folder=device.folderId)

            newdev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            newdev.model = device.model
            newdev.subModel = "Barometer"  # Manually need to set the model and subModel names (for UI only)
            newdev.replaceOnServer()

            devices = knownDevices[devAddress]['devices']
            devices.append(newdev.id)
            knownDevices.setitem_in_item(devAddress, 'devices', devices)
            knownDevices.setitem_in_item(devAddress, 'status', "Active")

        elif subType == '0x1A89':  # Wind Sensor

            self.logger.info(f"Adding Wind Direction subDevice to '{device.name}' ({device.id}) @ {devAddress}")

            newdev = indigo.device.create(indigo.kProtocol.Plugin,
                                          address=devAddress,
                                          name=device.name + " Wind Direction",
                                          deviceTypeId="discoveredDevice",
                                          groupWithDevice=device.id,
                                          props={'valueType': 'direction',
                                                 'configDone': True,
                                                 'AllowOnStateChange': False,
                                                 'SupportsOnState': False,
                                                 'SupportsSensorValue': True,
                                                 'SupportsStatusRequest': False
                                                 },
                                          folder=device.folderId)

            newdev.updateStateImageOnServer(indigo.kStateImageSel.WindDirectionSensor)
            newdev.model = device.model
            newdev.subModel = "Wind Direction"  # Manually need to set the model and subModel names (for UI only)
            newdev.replaceOnServer()

            devices = knownDevices[devAddress]['devices']
            devices.append(newdev.id)
            knownDevices.setitem_in_item(devAddress, 'devices', devices)
            knownDevices.setitem_in_item(devAddress, 'status', "Active")

        # all done creating devices.  Use the cached data to set initial data

        frameData = knownDevices[devAddress].get('frameData', None)
        if frameData:
            self.handler(frameData, knownDevices)

    def handler(self, frameData, knownDevices):

        devAddress = "OREGON-" + frameData['infos']['adr_channel']
        self.logger.threaddebug(f"Oregon frame received: {devAddress}")

        useFarenheit = indigo.activePlugin.pluginPrefs.get('useFarenheit', True)

        deviceList = knownDevices[devAddress]['devices']
        for deviceId in deviceList:

            try:
                sensor = indigo.devices[deviceId]
            except KeyError:
                self.logger.error(f"Device configuration error - invalid deviceId ({devAddress}) in device list: {str(knownDevices[devAddress])}")
                continue

            valueType = sensor.pluginProps.get('valueType', False)
            if not valueType:
                self.logger.error(f"Device configuration error - 'valueType' not configured: {devAddress}")
                return

            # only update battery on root device of group

            groupList = indigo.device.getGroupList(deviceId)
            if deviceId == groupList[0]:
                qualifier = frameData['infos']['qualifier']
                if int(qualifier) & 1:
                    sensor.updateStateOnServer('batteryLevel', '10', uiValue='10%')
                else:
                    sensor.updateStateOnServer('batteryLevel', '80', uiValue='80%')

            self.logger.threaddebug(f"{sensor.name}: Updating sensor {devAddress} with valueType = {valueType}")
            measures = frameData['infos']['measures']
            for x in measures:
                if x['type'] != valueType:
                    continue

                rawValue = x['value']

                if valueType == "temperature":
                    if not useFarenheit:
                        value = float(rawValue)
                        valueString = f"{value:.1f} °C"
                    else:
                        value = 9.0 / 5.0 * float(rawValue) + 32.0
                        valueString = f"{value:.1f} °F"

                elif valueType == "hygrometry":
                    value = int(rawValue)
                    valueString = f"{value:d}%"

                else:
                    self.logger.debug(f"Unknown valueType: {valueType}")
                    return

                sensor.updateStateOnServer('sensorValue', value, uiValue=valueString)
