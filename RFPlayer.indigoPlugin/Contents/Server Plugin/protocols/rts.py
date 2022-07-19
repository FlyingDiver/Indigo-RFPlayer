#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class RTS(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        devAddress = "RTS-" + frameData['infos']['id']
        if devAddress not in knownDevices:                                        
            indigo.server.log(f"New device added to Known Device list: {devAddress}")
            knownDevices[devAddress] = { 
                "status": "Available", 
                "devices": indigo.List(),
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
        self.logger.debug(f"{device.name}: Starting RTS device ({subType}) @ {devAddress}")
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
        newProps["SupportsSensorValue"] = False
        newProps["AllowOnStateChange"] = True
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(f"Configured RTS Sensor '{device.name}' ({device.id}) @ {devAddress}")

        # all done creating devices.  Use the cached data to set initial data
        
        frameData = knownDevices[devAddress].get('frameData', None)
        if frameData:
            self.handler(frameData, knownDevices)

    def handler(self, frameData, knownDevices):

        devAddress = "RTS-" + frameData['infos']['id']

        self.logger.threaddebug(f"RTS frame received: {devAddress}")
            
        deviceList = knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except KeyError:
                self.logger.error(f"Device configuration error - invalid deviceId ({devAddress}) in device list: {str(knownDevices[devAddress])}")
                continue
                
            sensorState = frameData['infos']['qualifier']
            self.logger.threaddebug(f"{sensor.name}: Updating sensor {devAddress} to {sensorState}")
            sensor.updateStateOnServer('sensorValue', sensorState, uiValue=sensorState)

    def requestStatus(self, rfPlayer):
        self.logger.debug(f"Ignored Request Status for {self.device.address}")
        return True

    def turnOn(self, rfPlayer):
        
        cmdString = f"on rts ID {self.device.address[4:]} qualifier 0"
        try:
            self.logger.debug(f"RTS turnOn command '{cmdString}' to {self.player.name}")
            rfPlayer.sendRawCommand(cmdString)
        except Exception as e:
            self.logger.exception(f"RTS turnOn command error: {str(e)}")
            return False
        else:
            return True

    def turnOff(self, rfPlayer):
        
        cmdString = "off rts ID %s qualifier 0" % (self.device.address[4:])        
        try:
            self.logger.debug(f"RTS turnOff command '{cmdString}' to {self.player.name}")
            rfPlayer.sendRawCommand(cmdString)
        except Exception as e:
            self.logger.exception(f"RTS turnOff command error: {str(e)}")
            return False
        else:
            return True

    def sendMyCommand(self, rfPlayer):
        
        cmdString = f"off rts ID {self.device.address[4:]} qualifier 4"
        try:
            self.logger.debug(f"RTS My command '{cmdString}' to {self.player.name}")
            rfPlayer.sendRawCommand(cmdString)
        except Exception as e:
            self.logger.exception(f"RTS My command error: {str(e)}")
            return False
        else:
            return True
