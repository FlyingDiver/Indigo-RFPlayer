#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class Visonic(object):

    @classmethod
    def getAddress(cls, frameData):
        return "VISONIC-" + frameData['infos']['id']

    @classmethod
    def getDescription(cls, frameData):
        return frameData['infos']['subTypeMeaning']

    @classmethod
    def getSubType(cls, frameData):
        return frameData['infos']['subType']

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.Visonic")
        self.device = device

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting Visonic device (%s) @ %s" % (device.name, subType, devAddress))
        
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

        self.logger.info(u"Configured Visonic Sensor '%s' (%s) @ %s" % (device.name, device.id, address))
       

    def handler(self, player, frameData):

        devAddress = "VISONIC-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: Visonic frame received: %s" % (player.device.name, devAddress))
            
        # Is this a configured device?
        self.logger.threaddebug(u"%s: Update pending, checking knownDevices = %s" % (player.device.name, str(self.knownDevices[devAddress])))
        
        if not (self.knownDevices[devAddress]['status'] == 'Active'):             # not in use
            self.logger.threaddebug(u"%s: Device %s not active, skipping update" % (player.device.name, devAddress))
            return
            
        deviceList = self.knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            if deviceId not in self.sensorDevices:
                self.logger.error(u"Device configuration error - 'Active' device not in sensor list: %s" % (devAddress))
                continue
                
            sensor = self.sensorDevices[deviceId]       
            sensorState = frameData['infos']['qualifier']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))                        
            sensor.updateStateOnServer('sensorValue', sensorState, uiValue=sensorState)
