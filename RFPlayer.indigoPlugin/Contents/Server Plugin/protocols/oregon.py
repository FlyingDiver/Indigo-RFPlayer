#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import indigo

class Oregon(object):

    @classmethod
    def frameCheck(cls, playerDevice, frameData, knownDevices):
        devAddress = "OREGON-" + frameData['infos']['adr_channel']
        if devAddress not in knownDevices:                                        
            indigo.server.log("New device added to Known Device list: %s" % (devAddress))
            knownDevices[devAddress] = { 
                "status": "Available", 
                "devices" : indigo.List(),
                "protocol": frameData['header']['protocol'], 
                "description": frameData['infos']['id_PHYMeaning'],
                "subType": frameData['infos']['id_PHY'],
                "playerId": playerDevice.id
            }
        else:
            knownDevices[devAddress]["playerId"] = playerDevice.id

        return devAddress
    
    def __init__(self, device, knownDevices):
        self.logger = logging.getLogger("Plugin.Oregon")
        self.device = device
        devAddress = device.pluginProps['address']
        self.player = indigo.devices[int(knownDevices[devAddress]['playerId'])]
        subType = knownDevices[devAddress]['subType']
        self.logger.debug(u"%s: Starting Oregon Scientific device (%s) @ %s" % (device.name, subType, devAddress))
        
        configDone = device.pluginProps.get('configDone', False)
        self.logger.threaddebug(u"%s: __init__ configDone = %s" % (device.name, str(configDone)))
        if configDone:
            return

        knownDevices.setitem_in_item(devAddress, 'status', "Active")
        devices = knownDevices[devAddress]['devices']
        devices.append(device.id)
        knownDevices.setitem_in_item(devAddress, 'devices', devices)
        
        # update the master device, depending on the actual device type 

        if subType not in ['0x1A89', '0x2A19', '0xDA78']: 
        
            device.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)
            device.name = devAddress + " Thermometer"
            device.subModel = "Thermometer"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "temperature"
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(u"Configured Oregon Scientific Temperature Sensor '%s' (%s) @ %s" % (device.name, device.id, devAddress))
       
        elif subType == '0x1A89':        # Wind Sensor
        
            device.updateStateImageOnServer(indigo.kStateImageSel.WindSpeedSensor)
            device.name = devAddress + " Wind Speed"
            device.subModel = "Wind Speed"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "speed"
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(u"Configured Oregon Scientific Wind Sensor '%s' (%s) @ %s" % (device.name, device.id, devAddress))

        elif subType == '0x2A19':        # Rain Sensor
        
            device.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensor)
            device.name = devAddress + " Rain Sensor"
            device.subModel = "Rain Sensor"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "rain"
            device.replacePluginPropsOnServer(newProps)
        
            self.logger.info(u"Configured Oregon Scientific Rain Sensor '%s' (%s) @ %s" % (device.name, device.id, devAddress))

        elif subType == '0xDA78':        # UV Sensor
        
            device.updateStateImageOnServer(indigo.kStateImageSel.LightSensor)
            device.name = devAddress + " UV Sensor"
            device.subModel = "UV Sensor"
            device.replaceOnServer()

            newProps = device.pluginProps
            newProps["configDone"] = True
            newProps["valueType"] = "uv"
            device.replacePluginPropsOnServer(newProps)

            self.logger.info(u"Configured Oregon Scientific UV Sensor '%s' (%s) @ %s" % (device.name, device.id, devAddress))

        else:
            self.logger.error(u"%s: Unknown Device Type = %s" % (subType))
            return
                
        # create any subdevices
 
        if subType in ['0x1A2D', '0xCA2C', '0x0ACC', '0x1A3D', '0xFA28']: 
    
            self.logger.info(u"Adding Hygrometer subDevice to '%s' (%s) @ %s" % (device.name, device.id, devAddress))

            newdev = indigo.device.create(indigo.kProtocol.Plugin, 
                                            address=devAddress,
                                            name=devAddress + " Hygrometer",
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

            devices = knownDevices[devAddress]['devices']
            devices.append(newdev.id)
            knownDevices.setitem_in_item(devAddress, 'devices', devices)
            knownDevices.setitem_in_item(devAddress, 'status', "Active")

        elif subType == '0x5A6D': 
       
            self.logger.info(u"Adding Barometer subDevice to '%s' (%s) @ %s" % (device.name, device.id, devAddress))

            newdev = indigo.device.create(indigo.kProtocol.Plugin, 
                                            address=devAddress,
                                            name=devAddress + " Barometer",
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
 
            devices = knownDevices[devAddress]['devices']
            devices.append(newdev.id)
            knownDevices.setitem_in_item(devAddress, 'devices', devices)
            knownDevices.setitem_in_item(devAddress, 'status', "Active")

        elif subType == '0x1A89':        # Wind Sensor

            self.logger.info(u"Adding Wind Direction subDevice to '%s' (%s) @ %s" % (device.name, device.id, devAddress))

            newdev = indigo.device.create(indigo.kProtocol.Plugin, 
                                            address=devAddress,
                                            name=devAddress + " Wind Direction",
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
 
            devices = knownDevices[devAddress]['devices']
            devices.append(newdev.id)
            knownDevices.setitem_in_item(devAddress, 'devices', devices)
            knownDevices.setitem_in_item(devAddress, 'status', "Active")



    def handler(self, player, frameData, knownDevices):

        devAddress = "OREGON-" + frameData['infos']['adr_channel']

        self.logger.threaddebug(u"%s: Oregon frame received: %s" % (player.device.name, devAddress))
         
        useFarenheit = indigo.activePlugin.pluginPrefs.get('useFarenheit', True)
           
        deviceList = knownDevices[devAddress]['devices']
        for deviceId in deviceList:
            try:
                sensor = indigo.devices[deviceId]
            except:
                self.logger.error(u"Device configuration error - invalid deviceId (%s) in device list: %s" % (devAddress, str(knownDevices[devAddress])))
                continue
                
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
                    if not useFarenheit:
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

