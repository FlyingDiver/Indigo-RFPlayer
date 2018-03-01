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
            self.logger.info("New Parrot Device %s" % (device.address))
            knownDevices[device.address] = { 
                "status": "Active", 
                "devices" : indigo.List(),
                "protocol": "11", 
                "description": device.address,
                "subType": 'None',
                "playerId": int(device.pluginProps["targetDevice"])
            }

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting Parrot device (%s) @ %s" % (device.name, subType, devAddress))
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

        self.logger.info(u"Configured Parrot device '%s' (%s) @ %s" % (device.name, device.id, devAddress))

    def handler(self, player, frameData, knownDevices):

        devAddress = "PARROT-" + frameData['infos']['idMeaning']

        self.logger.threaddebug(u"%s: Parrot frame received: %s" % (player.device.name, devAddress))
        
    def requestStatus(self, rfPlayer):
        self.logger.debug("Request Status for %s" % (self.device.address))        
        return True

    def turnOn(self, rfPlayer):
        self.logger.debug("Turn On for %s" % (self.device.address))
        
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
        self.logger.debug("Turn Off for %s" % (self.device.address))
        
        cmdString = "OFF %s PARROT" % (self.device.address[7:])
        
        try:
            self.logger.debug(u"Parrot turnOff command '" + cmdString + "' to " + self.player.name)
            rfPlayer.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"Parrot turnOff command error: %s" % str(e))
            return False
        else:
            return True
