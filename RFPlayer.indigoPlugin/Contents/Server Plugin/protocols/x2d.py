#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class X2D(object):

    @classmethod
    def getAddress(cls, frameData):
        return "X2D-" + frameData['infos']['id']

    @classmethod
    def getDescription(cls, frameData):
        return "X2D-" + frameData['infos']['id']

    @classmethod
    def getSubType(cls, frameData):
        return 'None'

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.X2D")
        self.device = device

        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting X2D device (%s) @ %s" % (device.name, subType, devAddress))
        
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

        self.logger.info(u"Configured X2D device '%s' (%s) @ %s" % (device.name, device.id, address))

    def handler(self, player, frameData):

        devAddress = "X2D-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: X2D frame received: %s" % (player.device.name, devAddress))

