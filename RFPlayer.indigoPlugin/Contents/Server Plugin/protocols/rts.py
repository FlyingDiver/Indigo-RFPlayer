class RTS(object):

    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.RTS")
        self.device = device
        self.logger.debug(u"%s: Starting RTS device" % device.name)

    def handler(self, player, frameData):

        devAddress = "RTS-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: RTS frame received: %s" % (player.device.name, devAddress))
    
        # make sure this device is in the list of known sensor devices
        
        if devAddress not in self.knownDevices:
            self.logger.info("New RTS Device %s" % (devAddress))
            self.knownDevices[devAddress] = { 
                "status": "Available", 
                "devices" : indigo.List(),
                "protocol": frameData['header']['protocol'], 
                "protocolMeaning": frameData['header']['protocolMeaning'], 
                "infoType": frameData['header']['infoType'], 
                "subType": frameData['infos']['subType'],
                "description": frameData['infos']['subTypeMeaning'],
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
            sensorState = frameData['infos']['qualifier']
            self.logger.threaddebug(u"%s: Updating sensor %s to %s" % (sensor.name, devAddress, sensorState))                        
            sensor.updateStateOnServer('sensorValue', sensorState, uiValue=sensorState)

    def configRTS(self, device):

        configDone = device.pluginProps.get('configDone', False)
        self.logger.debug(u" %s: configRTS, configDone = %s" % (device.name, str(configDone)))
        
        if configDone:
            return

        address = device.pluginProps['address']

        self.logger.threaddebug(u"configRTS (1) for knownDevices[%s] = %s" % (address, str(self.knownDevices[address])))

        self.knownDevices.setitem_in_item(address, 'status', "Active")
        devices = self.knownDevices[address]['devices']
        devices.append(device.id)
        self.knownDevices.setitem_in_item(address, 'devices', devices)

        self.logger.threaddebug(u"configRTS (2) for knownDevices[%s] = %s" % (address, str(self.knownDevices[address])))
        
        
        device.name = address
        device.replaceOnServer()

        newProps = device.pluginProps
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(u"Configured RTS Sensor '%s' (%s) @ %s" % (device.name, device.id, address))
