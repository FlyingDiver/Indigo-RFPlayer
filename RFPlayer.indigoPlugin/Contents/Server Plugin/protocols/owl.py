#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class Owl(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        devAddress = "OWL-" + frameData['infos']['id']
        if devAddress not in knownDevices:                                        
            indigo.server.log(f"New device added to Known Device list: {devAddress}")
            knownDevices[devAddress] = { 
                "status": "Available", 
                "devices": indigo.List(),
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
        self.logger = logging.getLogger("Plugin.Owl")
        self.device = device
        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(f"{device.name}: Starting Owl device ({subType}) @ {devAddress}")
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

        self.logger.info(f"Configured Owl device '{device.name}' ({device.id}) @ {address}")

        # all done creating devices.  Use the cached data to set initial data
        
        frameData = knownDevices[devAddress].get('frameData', None)
        if frameData:
            self.handler(frameData, knownDevices)

    def handler(self, frameData, knownDevices):

        devAddress = "OWL-" + frameData['infos']['id']
        self.logger.threaddebug(f"Owl frame received: {devAddress}")
