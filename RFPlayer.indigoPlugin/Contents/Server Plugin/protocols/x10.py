#! /usr/bin/env python
# -*- coding: utf-8 -*-

class X10(object):

    @classmethod
    def getAddress(cls, frameData):
        return "DOMIA-" + frameData['infos']['idMeaning']

    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.X10")
        self.device = device
        self.logger.debug(u"%s: Starting X10 device '%s'" % (device.name,device.address))


    def handler(self, player, frameData):

        devAddress = "X10-" + frameData['infos']['idMeaning']

        self.logger.threaddebug(u"%s: X10 frame received: %s" % (player.device.name, devAddress))
            
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
            sensorState = frameData['infos']['subType']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))                        
            sensor.updateStateOnServer('onOffState', bool(int(sensorState)))       
