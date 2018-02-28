#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class X10(object):

    @classmethod
    def getAddress(cls, frameData):
        return "X10-" + frameData['infos']['idMeaning']

    @classmethod
    def getDescription(cls, frameData):
        return "X10-" + frameData['infos']['idMeaning']

    @classmethod
    def getSubType(cls, frameData):
        return 'None'

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.X10")
        self.device = device

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting X10 device (%s) @ %s" % (device.name, subType, devAddress))
        
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

        self.logger.info(u"Configured X10 Sensor '%s' (%s) @ %s" % (device.name, device.id, address))


    def handler(self, player, frameData):

        devAddress = "X10-" + frameData['infos']['idMeaning']

        self.logger.threaddebug(u"%s: X10 frame received: %s" % (player.device.name, devAddress))
            
        deviceList = self.knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            if deviceId not in self.sensorDevices:
                self.logger.error(u"Device configuration error - 'Active' device not in sensor list: %s" % (devAddress))
                continue
                
            sensor = self.sensorDevices[deviceId]       
            sensorState = frameData['infos']['subType']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))                        
            sensor.updateStateOnServer('onOffState', bool(int(sensorState)))       
