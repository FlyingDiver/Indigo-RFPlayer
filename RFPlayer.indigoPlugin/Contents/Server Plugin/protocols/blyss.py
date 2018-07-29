#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class Blyss(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        devAddress = "BLYSS" + frameData['infos']['id']
        if devAddress not in knownDevices:                                        
            indigo.server.log("New device added to Known Device list: %s" % (devAddress))
            knownDevices[devAddress] = { 
                "status": "Available", 
                "devices" : indigo.List(),
                "protocol": frameData['header']['protocol'], 
                "description": frameData['infos']['id'],
                "subType": 'None',
                "playerId": playerDevice.id,
                "frameData": frameData
           }
        else:
            knownDevices[devAddress]["playerId"] = playerDevice.id

        return devAddress

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.Blyss")
        self.device = device
        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting Blyss device (%s) @ %s" % (device.name, subType, devAddress))
        self.player = indigo.devices[knownDevices[devAddress]['playerId']]
        
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

        self.logger.info(u"Configured Blyss device '%s' (%s) @ %s" % (device.name, device.id, address))
       
        # all done creating devices.  Use the cached data to set initial data
        
        frameData = knownDevices[devAddress].get('frameData', None)
        if (frameData):
            self.handler(frameData, knownDevices)
        

    def handler(self, frameData, knownDevices):

        devAddress = "BLYSS-" + frameData['infos']['id']
        self.logger.threaddebug(u"Blyss frame received: %s" % (devAddress))

