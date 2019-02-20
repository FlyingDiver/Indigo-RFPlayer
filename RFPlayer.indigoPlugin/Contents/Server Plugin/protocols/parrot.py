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
            self.logger.info("New Parrot Device {}".format(device.address))
            knownDevices[device.address] = { 
                "status": "Active", 
                "devices" : indigo.List(),
                "protocol": "11", 
                "description": device.address,
                "subType": 'None',
                "playerId": int(device.pluginProps["targetDevice"]),
                "frameData": None
            }

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"{}: Starting Parrot device ({}) @ {}".format(device.name, subType, devAddress))
        self.player = indigo.devices[knownDevices[devAddress]['playerId']]
        
        configDone = device.pluginProps.get('configDone', False)
        self.logger.threaddebug(u"{}: __init__ configDone = {}".format(device.name, str(configDone)))
        if configDone:
            return

        knownDevices.setitem_in_item(devAddress, 'status', "Active")
        devices = knownDevices[devAddress]['devices']
        devices.append(device.id)
        knownDevices.setitem_in_item(devAddress, 'devices', devices)
        
        newProps = device.pluginProps
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(u"Configured Parrot device '{}' ({}) @ {}".format(device.name, device.id, devAddress))

        # all done creating devices.  Use the cached data to set initial data
        
        frameData = knownDevices[devAddress].get('frameData', None)
        if (frameData):
            self.handler(frameData, knownDevices)
        
    def handler(self, frameData, knownDevices):

        devAddress = "PARROT-" + frameData['infos']['idMeaning']

        self.logger.threaddebug(u"Parrot frame received: %s" % (devAddress))

        deviceList = knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except:
                self.logger.error(u"Device configuration error - invalid deviceId (%s) in device list: %s" % (devAddress, str(knownDevices[devAddress])))
                continue
                                
            sensorState = frameData['infos']['subType']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))                        
            sensor.updateStateOnServer('onOffState', bool(int(sensorState)))       

        
    def requestStatus(self, rfPlayer):
        self.logger.debug("Request Status for %s" % (self.device.address))        
        return True

    def turnOn(self, rfPlayer):
        
        cmdString = "ON %s PARROT" % (self.device.address[7:])        
        try:
            self.logger.debug(u"Parrot turnOn command '" + cmdString + "' to " + self.player.name)
            rfPlayer.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"Parrot turnOn command error: %s" % str(e))
            return False
        else:
            return True

    def turnOff(self, rfPlayer):
        
        cmdString = "OFF %s PARROT" % (self.device.address[7:])        
        try:
            self.logger.debug(u"Parrot turnOff command '" + cmdString + "' to " + self.player.name)
            rfPlayer.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"Parrot turnOff command error: %s" % str(e))
            return False
        else:
            return True
