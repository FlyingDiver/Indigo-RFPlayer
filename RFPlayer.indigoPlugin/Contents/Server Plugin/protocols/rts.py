#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class RTS(object):

    @classmethod
    def getAddress(cls, frameData):
        return "RTS-" + frameData['infos']['id']

    @classmethod
    def getDescription(cls, frameData):
        return frameData['infos']['subTypeMeaning']

    @classmethod
    def getSubType(cls, frameData):
        return frameData['infos']['subType']

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.RTS")
        self.device = device

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting Oregon Scientific device (%s) @ %s" % (device.name, subType, devAddress))
        
        configDone = device.pluginProps.get('configDone', False)
        self.logger.threaddebug(u"%s: __init__ configDone = %s" % (device.name, str(configDone)))
        if configDone:
            return

        knownDevices.setitem_in_item(devAddress, 'status', "Active")
        devices = knownDevices[devAddress]['devices']
        devices.append(device.id)
        knownDevices.setitem_in_item(devAddress, 'devices', devices)
                
        device.name = address
        device.replaceOnServer()

        newProps = device.pluginProps
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(u"Configured RTS Sensor '%s' (%s) @ %s" % (device.name, device.id, address))


    def handler(self, player, frameData):

        devAddress = "RTS-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: RTS frame received: %s" % (player.device.name, devAddress))            
            
        deviceList = self.knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except:
                self.logger.error(u"Device configuration error - invalid deviceId (%s) in device list: %s" % (devAddress, str(knownDevices[devAddress])))
                continue
                
            sensorState = frameData['infos']['qualifier']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))                        
            sensor.updateStateOnServer('sensorValue', sensorState, uiValue=sensorState)

