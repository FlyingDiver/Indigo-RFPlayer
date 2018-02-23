    def x10Handler(self, player, frameData):

        devAddress = "X10-" + frameData['infos']['idMeaning']

        self.logger.debug(u"%s: X10 frame received: %s" % (player.device.name, devAddress))

        # make sure this device is in the list of known sensor devices
        
        if devAddress not in self.knownDevices:
            self.logger.info("New X10 Device %s" % (devAddress))
            self.knownDevices[devAddress] = { 
                "status": "Available", 
                "devices" : indigo.List(),
                "protocol": frameData['header']['protocol'], 
                "protocolMeaning": frameData['header']['protocolMeaning'], 
                "infoType": frameData['header']['infoType'], 
                "subType": 'None',
                "description": devAddress,
            }
            self.logger.debug(u"added new known device: %s = %s" % (devAddress, unicode(self.knownDevices[devAddress])))
            
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
