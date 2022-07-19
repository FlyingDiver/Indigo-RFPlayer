#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo


class Parrot(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        return "PARROT-" + frameData['infos']['idMeaning']

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.Parrot")
        self.device = device

        if device.address not in knownDevices:
            self.logger.info(f"New Parrot Device {device.address}")
            knownDevices[device.address] = {
                "status": "Active",
                "devices": indigo.List(),
                "protocol": "11",
                "description": device.address,
                "subType": 'None',
                "playerId": int(device.pluginProps["targetDevice"]),
                "frameData": None
            }

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(f"{device.name}: Starting Parrot device ({subType}) @ {devAddress}")
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

        self.logger.info(f"Configured Parrot device '{device.name}' ({device.id}) @ {devAddress}")

        # all done creating devices.  Use the cached data to set initial data

        frameData = knownDevices[devAddress].get('frameData', None)
        if frameData:
            self.handler(frameData, knownDevices)

    def handler(self, frameData, knownDevices):

        devAddress = "PARROT-" + frameData['infos']['idMeaning']

        self.logger.threaddebug(f"Parrot frame received: {devAddress}")

        deviceList = knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except KeyError:
                self.logger.error(
                    f"Device configuration error - invalid deviceId ({devAddress}) in device list: {str(knownDevices[devAddress])}")
                continue

            sensorState = frameData['infos']['subType']
            self.logger.threaddebug(f"{sensor.name}: Updating sensor {devAddress} to {sensorState}")
            sensor.updateStateOnServer('onOffState', bool(int(sensorState)))

    def requestStatus(self, rfPlayer):
        self.logger.debug(f"Request Status for {self.device.address}")
        return True

    def turnOn(self, rfPlayer):

        cmdString = f"ON {self.device.address[7:]} PARROT"
        try:
            self.logger.debug(f"Parrot turnOn command '{cmdString}' to {self.player.name}")
            rfPlayer.sendRawCommand(cmdString)
        except Exception as e:
            self.logger.exception(f"Parrot turnOn command error: {str(e)}")
            return False
        else:
            return True

    def turnOff(self, rfPlayer):

        cmdString = f"OFF {self.device.address[7:]} PARROT"
        try:
            self.logger.debug(f"Parrot turnOff command '{cmdString}' to {self.player.name}")
            rfPlayer.sendRawCommand(cmdString)
        except Exception as e:
            self.logger.exception(f"Parrot turnOff command error: {e}")
            return False
        else:
            return True
