#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class RTS(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        devAddress = "RTS-" + frameData['infos']['id']
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
        self.logger = logging.getLogger("Plugin.RTS")
        self.device = device
        devAddress = device.pluginProps['address']
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting RTS device (%s) @ %s" % (device.name, subType, devAddress))
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
        newProps["SupportsSensorValue"] = False
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(u"Configured RTS Sensor '%s' (%s) @ %s" % (device.name, device.id, address))

        # all done creating devices.  Use the cached data to set initial data
        
        frameData = knownDevices[devAddress].get('frameData', None)
        if (frameData):
            self.handler(frameData, knownDevices)
        

    def handler(self, frameData, knownDevices):

        devAddress = "RTS-" + frameData['infos']['id']

        self.logger.threaddebug(u"RTS frame received: %s" % (devAddress))            
            
        deviceList = self.knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except:
                self.logger.error(u"Device configuration error - invalid deviceId (%s) in device list: %s" % (devAddress, str(knownDevices[devAddress])))
                continue
                
            sensorState = frameData['infos']['qualifier']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))                        
            sensor.updateStateOnServer('sensorValue', sensorState, uiValue=sensorState)

    def requestStatus(self, rfPlayer):
        self.logger.debug("Request Status for %s" % (self.device.address))        
        return True

    def turnOn(self, rfPlayer):
        
        cmdString = "on rts %s qualifier 0" % (self.device.address[4:])        
        try:
            self.logger.debug(u"RTS turnOn command '" + cmdString + "' to " + self.player.name)
            rfPlayer.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"RTS turnOn command error: %s" % str(e))
            return False
        else:
            return True

    def turnOff(self, rfPlayer):
        
        cmdString = "off rts %s qualifier 0" % (self.device.address[4:])        
        try:
            self.logger.debug(u"RTS turnOff command '" + cmdString + "' to " + self.player.name)
            rfPlayer.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"RTS turnOff command error: %s" % str(e))
            return False
        else:
            return True

    def sendMyCommand(self, rfPlayer):
        
        cmdString = "off rts %s qualifier 4" % (self.device.address[4:])        
        try:
            self.logger.debug(u"RTS My command '" + cmdString + "' to " + self.player.name)
            rfPlayer.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"RTS My command error: %s" % str(e))
            return False
        else:
            return True
