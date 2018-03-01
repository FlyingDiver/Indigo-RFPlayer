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
            self.logger.info("New X10 Device %s" % (device.address))
            knownDevices[device.address] = { 
                "status": "Active", 
                "devices" : indigo.List(),
                "protocol": "1", 
                "subType": deviceType,
                "description": device.address,
                "playerId": int(device.pluginProps["targetDevice"])
          }

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting X10 device (%s) @ %s" % (device.name, subType, devAddress))
        self.player = indigo.devices[knownDevices[devAddress]['playerId']]
        
        configDone = device.pluginProps.get('configDone', False)
        self.logger.threaddebug(u"%s: __init__ configDone = %s" % (device.name, str(configDone)))
        if configDone:
            return

        knownDevices.setitem_in_item(devAddress, 'status', "Active")
        devices = knownDevices[devAddress]['devices']
        devices.append(device.id)
        knownDevices.setitem_in_item(devAddress, 'devices', devices)
        
        device.name = devAddress
        device.replaceOnServer()

        newProps = device.pluginProps
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(u"Configured X10 Sensor '%s' (%s) @ %s" % (device.name, device.id, devAddress))


    def handler(self, player, frameData, knownDevices):

        devAddress = "X10-" + frameData['infos']['idMeaning']

        self.logger.threaddebug(u"%s: X10 frame received: %s" % (player.device.name, devAddress))
            
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
        self.logger.debug("Turn On for %s" % (self.device.address))
        
        cmdString = "ON %s X10" % (self.device.address[4:])
        
        try:
            self.logger.debug(u"X10 turnOn command '" + cmdString + "' to " + self.player.name)
            rfPlayer.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"X10 turnOn command error: %s" % str(e))
            return False
        else:
            return True

    def turnOff(self, rfPlayer):
        self.logger.debug("Turn Off for %s" % (self.device.address))
        
        cmdString = "OFF %s X10" % (self.device.address[4:])
        
        try:
            self.logger.debug(u"X10 turnOff command '" + cmdString + "' to " + self.player.name)
            rfPlayer.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"X10 turnOff command error: %s" % str(e))
            return False
        else:
            return True
