#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo


class X10(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        return "X10-" + frameData['infos']['idMeaning']

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.X10")
        self.device = device
        deviceType = device.pluginProps['deviceType']

        if device.address not in knownDevices:
            self.logger.info(f"New X10 Device {device.address}")
            knownDevices[device.address] = {
                "status": "Active",
                "devices": indigo.List(),
                "protocol": "1",
                "subType": deviceType,
                "description": device.address,
                "playerId": int(device.pluginProps["targetDevice"]),
                "frameData": None
            }

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(f"{device.name}: Starting X10 device ({subType}) @ {devAddress}")
        self.player = indigo.devices[knownDevices[devAddress]['playerId']]

        configDone = device.pluginProps.get('configDone', False)
        self.logger.threaddebug(f"{device.name}: __init__ configDone = {str(configDone)}")
        if configDone:
            return

        knownDevices.setitem_in_item(devAddress, 'status', "Active")
        devices = knownDevices[devAddress]['devices']
        devices.append(device.id)
        knownDevices.setitem_in_item(devAddress, 'devices', devices)

        newProps = device.pluginProps
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(f"Configured X10 Sensor '{device.name}' ({device.id}) @ {devAddress}")

        # all done creating devices.  Use the cached data to set initial data

        frameData = knownDevices[devAddress].get('frameData', None)
        if frameData:
            self.handler(frameData, knownDevices)

    def handler(self, frameData, knownDevices):

        devAddress = "X10-" + frameData['infos']['idMeaning']
        self.logger.threaddebug(f"X10 frame received: {devAddress}")

        deviceList = knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except KeyError:
                self.logger.error(f"Device configuration error - invalid deviceId ({devAddress}) in device list: {str(knownDevices[devAddress])}")
                continue

            sensorState = frameData['infos']['subType']
            self.logger.threaddebug(f"{sensor.name}: Updating sensor {devAddress} to {sensorState}")
            sensor.updateStateOnServer('onOffState', bool(int(sensorState)))

    def requestStatus(self, rfPlayer):
        self.logger.debug(f"Request Status for {self.device.address}")
        return True

    def turnOn(self, rfPlayer):

        cmdString = f"ON {self.device.address[4:]} X10"
        try:
            self.logger.debug(f"X10 turnOn command '{cmdString}' to {self.player.name}")
            rfPlayer.sendRawCommand(cmdString)
        except Exception as e:
            self.logger.exception(f"X10 turnOn command error: {str(e)}")
            return False
        else:
            return True

    def turnOff(self, rfPlayer):

        cmdString = "OFF %s X10" % (self.device.address[4:])
        try:
            self.logger.debug(f"X10 turnOff command '{cmdString}' to {self.player.name}")
            rfPlayer.sendRawCommand(cmdString)
        except Exception as e:
            self.logger.exception(f"X10 turnOff command error: {str(e)}")
            return False
        else:
            return True
