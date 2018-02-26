#! /usr/bin/env python
# -*- coding: utf-8 -*-

class Oregon(object):

    @classmethod
    def getAddress(cls, frameData):
        return "OREGON-" + frameData['infos']['adr_channel']

    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.Oregon")
        self.device = device
        self.logger.debug(u"%s: Starting Oregon Scientific device" % device.name)

    def handler(self, player, frameData):

        devAddress = "OREGON-" + frameData['infos']['adr_channel']

        self.logger.threaddebug(u"%s: Oregon frame received: %s" % (player.device.name, devAddress))
                    
        deviceList = self.knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            if deviceId not in self.sensorDevices:
                self.logger.error(u"Device configuration error - 'Active' device not in sensor list: %s" % (devAddress))
                continue
            
            sensor = self.sensorDevices[deviceId]
            valueType = sensor.pluginProps.get('valueType', False)
            if not valueType:
                self.logger.error(u"Device configuration error - 'valueType' not configured: %s" % (devAddress))
                return
        
            self.logger.threaddebug(u"%s: Updating sensor %s with valueType = %s" % (sensor.name, devAddress, valueType))
            measures = frameData['infos']['measures']
            for x in measures:
                if x['type'] != valueType:
                    continue
                
                rawValue = x['value']
                
                if valueType == "temperature":
                    if not self.useFarenheit:
                        value = float(rawValue)
                        valueString = u"%.1f °C" % value
                    else:
                        value = 9.0/5.0 * float(rawValue) + 32.0
                        valueString = u"%.1f °F" % value
                
                elif valueType == "hygrometry":
                    value = int(rawValue)
                    valueString = "%d%%" % value
        
                else:
                    self.logger.debug(u"Unknown valueType: %s" % (valueType))
                    return
                        
                sensor.updateStateOnServer('sensorValue', value, uiValue=valueString)

            
    def configOregon(self, device):

        configDone = device.pluginProps.get('configDone', False)
        self.logger.debug(u" %s: configOregon, configDone = %s" % (device.name, str(configDone)))
        
        if configDone:
            return

        address = device.pluginProps['address']

        self.logger.threaddebug(u"configOregon (1) for knownDevices[%s] = %s" % (address, str(self.knownDevices[address])))

        self.knownDevices.setitem_in_item(address, 'status', "Active")
        devices = self.knownDevices[address]['devices']
        devices.append(device.id)
        self.knownDevices.setitem_in_item(address, 'devices', devices)

        self.logger.threaddebug(u"configOregon (2) for knownDevices[%s] = %s" % (address, str(self.knownDevices[address])))
        
        # update the master device, depending on the actual device type 
        
        id_PHY = self.knownDevices[address]['subType']
        
        if id_PHY not in ['0x1A89', '0x2A19', '0xDA78']: 
        
            device.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)
            device.name = address + " Thermometer"
            device.subModel = "Thermometer"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "temperature"
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(u"Configured Oregon Scientific Temperature Sensor '%s' (%s) @ %s" % (device.name, device.id, address))
       
        elif id_PHY == '0x1A89':        # Wind Sensor
        
            device.updateStateImageOnServer(indigo.kStateImageSel.WindSpeedSensor)
            device.name = address + " Wind Speed"
            device.subModel = "Wind Speed"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "speed"
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(u"Configured Oregon Scientific Wind Sensor '%s' (%s) @ %s" % (device.name, device.id, address))

        elif id_PHY == '0x2A19':        # Rain Sensor
        
            device.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensor)
            device.name = address + " Rain Sensor"
            device.subModel = "Rain Sensor"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "rain"
            device.replacePluginPropsOnServer(newProps)
        
            self.logger.info(u"Configured Oregon Scientific Rain Sensor '%s' (%s) @ %s" % (device.name, device.id, address))

        elif id_PHY == '0xDA78':        # UV Sensor
        
            device.updateStateImageOnServer(indigo.kStateImageSel.LightSensor)
            device.name = address + " UV Sensor"
            device.subModel = "UV Sensor"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "uv"
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(u"Configured Oregon Scientific UV Sensor '%s' (%s) @ %s" % (device.name, device.id, address))

        else:
            self.logger.error(u"%s: Unknown Device Type = %s" % (id_PHY))
            return
                
        # create any subdevices
 
        if id_PHY in ['0x1A2D', '0xCA2C', '0x0ACC', '0x1A3D', '0xFA28']: 
    
            self.logger.info(u"Adding Hygrometer subDevice to '%s' (%s) @ %s" % (device.name, device.id, address))

            newdev = indigo.device.create(indigo.kProtocol.Plugin, 
                                            address=address,
                                            name=address + " Hygrometer",
                                            deviceTypeId="oregonDevice", 
                                            groupWithDevice=device.id,
                                            props={ 'valueType': 'hygrometry',
                                                    'configDone': True, 
                                                    'AllowOnStateChange': False,
                                                    'SupportsOnState': False,
                                                    'SupportsSensorValue': True,
                                                    'SupportsStatusRequest': False
                                                },
                                            folder=device.folderId)
                                                    
            newdev.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensor)
            newdev.model = device.model
            newdev.subModel = "Hygrometer"       # Manually need to set the model and subModel names (for UI only)
            newdev.replaceOnServer()    

            devices = self.knownDevices[address]['devices']
            devices.append(newdev.id)
            self.knownDevices.setitem_in_item(address, 'devices', devices)
            self.knownDevices.setitem_in_item(address, 'status', "Active")


        elif id_PHY == '0x5A6D': 
       
            self.logger.info(u"Adding Barometer subDevice to '%s' (%s) @ %s" % (device.name, device.id, address))

            newdev = indigo.device.create(indigo.kProtocol.Plugin, 
                                            address=address,
                                            name=address + " Barometer",
                                            deviceTypeId="oregonDevice", 
                                            groupWithDevice=device.id,
                                            props={ 'valueType': 'pressure',
                                                    'configDone': True, 
                                                    'AllowOnStateChange': False,
                                                    'SupportsOnState': False,
                                                    'SupportsSensorValue': True,
                                                    'SupportsStatusRequest': False
                                                },
                                            folder=device.folderId)
                                        
            newdev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            newdev.model = device.model
            newdev.subModel = "Barometer"       # Manually need to set the model and subModel names (for UI only)
            newdev.replaceOnServer()    
 
            devices = self.knownDevices[address]['devices']
            devices.append(newdev.id)
            self.knownDevices.setitem_in_item(address, 'devices', devices)
            self.knownDevices.setitem_in_item(address, 'status', "Active")

        elif id_PHY == '0x1A89':        # Wind Sensor

            self.logger.info(u"Adding Wind Direction subDevice to '%s' (%s) @ %s" % (device.name, device.id, address))

            newdev = indigo.device.create(indigo.kProtocol.Plugin, 
                                            address=address,
                                            name=address + " Wind Direction",
                                            deviceTypeId="oregonDevice", 
                                            groupWithDevice=device.id,
                                            props={ 'valueType': 'direction',
                                                    'configDone': True, 
                                                    'AllowOnStateChange': False,
                                                    'SupportsOnState': False,
                                                    'SupportsSensorValue': True,
                                                    'SupportsStatusRequest': False
                                                },
                                            folder=device.folderId)
                                        
            newdev.updateStateImageOnServer(indigo.kStateImageSel.WindDirectionSensor)
            newdev.model = device.model
            newdev.subModel = "Wind Direction"       # Manually need to set the model and subModel names (for UI only)
            newdev.replaceOnServer()    

            devices = self.knownDevices[address]['devices']
            devices.append(newdev.id)
            self.knownDevices.setitem_in_item(address, 'devices', devices)
            self.knownDevices.setitem_in_item(address, 'status', "Active")

        self.logger.debug(u"configOregon done, knownDevices = %s" % (str(self.knownDevices)))
 