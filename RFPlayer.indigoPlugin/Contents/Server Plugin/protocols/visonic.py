#! /usr/bin/env python
# -*- coding: utf-8 -*-

class Visonic(object):

    @classmethod
    def getAddress(cls, frameData):
        return "VISONIC-" + frameData['infos']['id']


    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.Visonic")
        self.device = device
        self.logger.debug(u"%s: Starting Visonic device" % device.name)

    def handler(self, player, frameData):

        devAddress = "VISONIC-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: Visonic frame received: %s" % (player.device.name, devAddress))
            
        # Is this a configured device?
        self.logger.threaddebug(u"%s: Update pending, checking knownDevices = %s" % (player.device.name, str(self.knownDevices[devAddress])))
        
        if not (self.knownDevices[devAddress]['status'] == 'Active'):             # not in use
            self.logger.threaddebug(u"%s: Device %s not active, skipping update" % (player.device.name, devAddress))
            return
            
        deviceList = self.knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            if deviceId not in self.sensorDevices:
                self.logger.error(u"Device configuration error - 'Active' device not in sensor list: %s" % (devAddress))
                continue
                
            sensor = self.sensorDevices[deviceId]       
            sensorState = frameData['infos']['qualifier']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))                        
            sensor.updateStateOnServer('sensorValue', sensorState, uiValue=sensorState)

    def configVisonic(self, device):

        configDone = device.pluginProps.get('configDone', False)
        self.logger.debug(u" %s: configVisonic, configDone = %s" % (device.name, str(configDone)))
        
        if configDone:
            return

        address = device.pluginProps['address']

        self.logger.threaddebug(u"configVisonic (1) for knownDevices[%s] = %s" % (address, str(self.knownDevices[address])))

        self.knownDevices.setitem_in_item(address, 'status', "Active")
        devices = self.knownDevices[address]['devices']
        devices.append(device.id)
        self.knownDevices.setitem_in_item(address, 'devices', devices)

        self.logger.threaddebug(u"configVisonic (2) for knownDevices[%s] = %s" % (address, str(self.knownDevices[address])))
        
        
        device.name = address
        device.replaceOnServer()

        newProps = device.pluginProps
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(u"Configured Visonic Sensor '%s' (%s) @ %s" % (device.name, device.id, address))
       
