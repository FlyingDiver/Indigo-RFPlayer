#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class Visonic(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        devAddress = "VISONIC-" + frameData['infos']['id']
        if devAddress not in knownDevices:                                        
            indigo.server.log("New device added to Known Device list: %s" % (devAddress))
            knownDevices[devAddress] = { 
                "status": "Available", 
                "devices" : indigo.List(),
                "protocol": frameData['header']['protocol'], 
                "description": frameData['infos']['subTypeMeaning'],
                "subType": frameData['infos']['subType'],
                "playerId": playerDevice.id,
                "frameData": frameData
            }
        else:
            knownDevices[devAddress]["playerId"] = playerDevice.id

        return devAddress

    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.Visonic")
        self.device = device
        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting Visonic device (%s) @ %s" % (device.name, subType, devAddress))
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

        self.logger.info(u"Configured Visonic Sensor '%s' (%s) @ %s" % (device.name, device.id, devAddress))
       
        # all done creating devices.  Use the cached data to set initial data
        
        frameData = knownDevices[devAddress].get('frameData', None)
        if (frameData):
            self.handler(frameData, knownDevices)
        

    def handler(self, frameData, knownDevices):

        devAddress = "VISONIC-" + frameData['infos']['id']

        self.logger.threaddebug(u"Visonic frame received: %s" % (devAddress))
            
        deviceList = knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except:
                self.logger.error(u"Device configuration error - invalid deviceId (%s) in device list: %s" % (devAddress, str(knownDevices[devAddress])))
                continue

            sensorState = frameData['infos']['qualifier']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))
            if int(sensorState) & 4:
                sensor.updateStateOnServer('batteryLevel', '10', uiValue='10%')
            else:
                sensor.updateStateOnServer('batteryLevel', '80', uiValue='80%')
            
            if sensorState == '0':
                sensor.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            else:
                sensor.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
            sensor.updateStateOnServer('sensorValue', sensorState, uiValue=sensorState)

            if int(sensorState) & 9:    # bits 0 and 3 are faults
                sensor.updateStateOnServer('faultCode', sensorState)
                indigo.activePlugin.triggerCheck(sensor)
            else:
                sensor.updateStateOnServer('faultCode', None)
            
