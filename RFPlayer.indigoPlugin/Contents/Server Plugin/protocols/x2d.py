#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class X2D(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        devAddress = "X2D-" + frameData['infos']['id']
        if devAddress not in knownDevices:                                        
            indigo.server.log(f"New device added to Known Device list: {devAddress}")
            knownDevices[devAddress] = { 
                "status": "Available", 
                "devices": indigo.List(),
                "protocol": frameData['header']['protocol'], 
                "description": frameData['infos']['id'],
                "playerId": playerDevice.id,
                "subType": 'None',
                "frameData": frameData
            }
        else:
            knownDevices[devAddress]["playerId"] = playerDevice.id
        return devAddress

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.X2D")
        self.device = device
        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(f"{device.name}: Starting X2D device ({subType}) @ {devAddress}")
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

        self.logger.info(f"Configured X2D device '{device.name}' ({device.id}) @ {address}")

        # all done creating devices.  Use the cached data to set initial data
        
        frameData = knownDevices[devAddress].get('frameData', None)
        if frameData:
            self.handler(frameData, knownDevices)

    def handler(self, frameData, knownDevices):

        devAddress = "X2D-" + frameData['infos']['id']
        self.logger.threaddebug(f"X2D frame received: {devAddress}")

        deviceList = knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except KeyError:
                self.logger.error(f"Device configuration error - invalid deviceId ({devAddress}) in device list: {str(knownDevices[devAddress])}")
                continue

            sensorState = frameData['infos']['qualifier']
            self.logger.threaddebug(f"{sensor.name}: Updating sensor {devAddress} to {sensorState}")
            if int(sensorState) & 4:
                sensor.updateStateOnServer('batteryLevel', '10', uiValue='10%')
            else:
                sensor.updateStateOnServer('batteryLevel', '80', uiValue='80%')
            
            if int(sensorState) & 3:    # bits 0 and 1 are faults
                sensor.updateStateOnServer('faultCode', sensorState)
                indigo.activePlugin.triggerCheck(sensor)
            else:
                sensor.updateStateOnServer('faultCode', None)
            
