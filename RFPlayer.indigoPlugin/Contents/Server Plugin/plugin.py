#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys
import time
from datetime import datetime
import logging

from ghpu import GitHubPluginUpdater

from RFPlayer import RFPlayer

kCurDevVersCount = 0        # current version of plugin devices


################################################################################
class Plugin(indigo.PluginBase):

    ########################################
    # Main Plugin methods
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        try:
            self.logLevel = int(self.pluginPrefs[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"RFPlayer logLevel = " + str(self.logLevel))

    def startup(self):
        self.logger.info(u"Starting RFPlayer")

        self.useFarenheit = self.pluginPrefs.get('useFarenheit', True)
        self.knownDevices = indigo.activePlugin.pluginPrefs.get(u"knownDevices", indigo.Dict())

        self.players = { }
        self.sensorDevices = {}
        
        self.protocolHandlers = {
            "1"  : self.x10Handler,
            "2"  : self.visonicHandler,
            "3"  : self.blyssHandler,
            "4"  : self.chaconHandler,
            "5"  : self.oregonHandler,
            "6"  : self.domiaHandler,
            "7"  : self.owlHandler,
            "8"  : self.x2dHandler,
            "9"  : self.rtsHandler,
            "10" : self.kd101Handler,
            "11" : self.parrotHandler
        }
        
        self.updater = GitHubPluginUpdater(self)
        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
        self.logger.debug(u"RFPlayer updateFrequency = " + str(self.updateFrequency))
        self.next_update_check = time.time()

    def shutdown(self):
        indigo.activePlugin.pluginPrefs[u"knownDevices"] = self.knownDevices
        self.logger.info(u"Shutting down RFPlayer")


    def runConcurrentThread(self):

        try:
            while True:

                for playerID, player in self.players.items():
                    playerFrame = player.poll()
                    if playerFrame:
                        if 'systemStatus' in playerFrame:
                            self.logger.debug(u"%s: systemStatus received" % (player.device.name))
                    
                        elif 'radioStatus' in playerFrame:
                            self.logger.debug(u"%s: radioStatus received" % (player.device.name))
               
                        elif 'parrotStatus' in playerFrame:
                            self.logger.debug(u"%s: parrotStatus received" % (player.device.name))
               
                        elif 'transcoderStatus' in playerFrame:
                            self.logger.debug(u"%s: transcoderStatus received" % (player.device.name))
               
                        elif 'frame' in playerFrame:                        # async frame received - dispatch to the handler for the frame's protocol
            
                            protocol = playerFrame['frame']['header']['protocol']
                            if protocol in self.protocolHandlers:
                                self.protocolHandlers[protocol](player, playerFrame['frame'])
                            else:
                                self.logger.error(u"%s: Unknown protocol:\n" %  (player.device.name, str(playerFrame)))      
            
                        else:
                            self.logger.error(u"%s: Unknown playerFrame:\n" %  (player.device.name, str(playerFrame)))      
    
                if (self.updateFrequency > 0.0) and (time.time() > self.next_update_check):
                    self.next_update_check = time.time() + self.updateFrequency
                    self.updater.checkForUpdate()

                self.sleep(0.1)

        except self.stopThread:
            for playerID, player in self.players.items():
                player.stop()            
            

    ########################################
    # Plugin Preference Methods
    ########################################

    def validatePrefsConfigUi(self, valuesDict):
        errorDict = indigo.Dict()

        try:
            self.logLevel = int(valuesDict[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)

        updateFrequency = int(valuesDict['updateFrequency'])
        if (updateFrequency < 0) or (updateFrequency > 24):
            errorDict['updateFrequency'] = u"Update frequency is invalid - enter a valid number (between 0 and 24)"

        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)
        return (True, valuesDict)

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            try:
                self.logLevel = int(valuesDict[u"logLevel"])
            except:
                self.logLevel = logging.INFO
            self.indigo_log_handler.setLevel(self.logLevel)

            self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
            self.next_update_check = time.time() + self.updateFrequency


    ########################################
    # Device Management Methods
    ########################################

    def didDeviceCommPropertyChange(self, origDev, newDev):
    
        if newDev.deviceTypeId == "RFPlayer":
            if origDev.pluginProps.get('serialPort', None) != newDev.pluginProps.get('serialPort', None):
                return True           

        return False
      
    def deviceStartComm(self, device):

        instanceVers = int(device.pluginProps.get('devVersCount', 0))
        if instanceVers == kCurDevVersCount:
            self.logger.threaddebug(u"%s: Device is current version: %d" % (device.name ,instanceVers))
        elif instanceVers < kCurDevVersCount:
            newProps = device.pluginProps

            # do version specific updates here
            
            newProps["devVersCount"] = kCurDevVersCount
            device.replacePluginPropsOnServer(newProps)
            device.stateListOrDisplayStateIdChanged()
            self.logger.debug(u"%s: Updated device version: %d -> %d" % (device.name,  instanceVers, kCurDevVersCount))
        else:
            self.logger.warning(u"%s: Invalid device version: %d" % (device.name, instanceVers))

        # Now do the device-specific startup work
        
        if device.deviceTypeId == "RFPlayer":
            self.logger.debug(u"%s: Starting RFPlayer interface device" % device.name)
            serialPort = device.pluginProps.get(u'serialPort', "")
            baudRate = int(device.pluginProps.get(u'baudRate', 0))
            player = RFPlayer(self, device)
            player.start(serialPort, baudRate)
            self.players[device.id] = player
                
        elif device.deviceTypeId == "x10Device":
            self.logger.debug(u"%s: Starting X10 device '%s'" % (device.name,device.address))
            houseCode = device.pluginProps['houseCode']
            unitCode = device.pluginProps['unitCode']
            device.name = device.address
            device.replaceOnServer()
            self.sensorDevices[device.id] = device
            if device.address not in self.knownDevices:
                self.logger.info("New X10 Device %s" % (device.address))
                self.knownDevices[device.address] = { 
                    "status": "Active", 
                    "devices" : [device.id],
                    "protocol": "1", 
                    "protocolMeaning": "X10", 
                    "infoType": "0", 
                    "subType": 'None',
                    "description": device.address,
                }
                self.logger.debug(u"added new known device: %s = %s" % (device.address, unicode(self.knownDevices[device.address])))

        elif device.deviceTypeId == "parrotDevice":
            self.logger.debug(u"%s: Starting Parrot device '%s'" % (device.name,device.address))
            houseCode = device.pluginProps['houseCode']
            unitCode = device.pluginProps['unitCode']
            device.name = device.address
            device.replaceOnServer()
            self.sensorDevices[device.id] = device
            if device.address not in self.knownDevices:
                self.logger.info("New Parrot Device %s" % (device.address))
                self.knownDevices[device.address] = { 
                    "status": "Active", 
                    "devices" : [device.id],
                    "protocol": "1", 
                    "protocolMeaning": "Parrot", 
                    "infoType": "0", 
                    "subType": 'None',
                    "description": device.address,
                }
                self.logger.debug(u"added new known device: %s = %s" % (device.address, unicode(self.knownDevices[device.address])))

              
        elif device.deviceTypeId == "visonicDevice":
            self.logger.debug(u"%s: Starting Visonic device" % device.name)
            self.configVisonic(device)
            self.sensorDevices[device.id] = device
               
        elif device.deviceTypeId == "oregonDevice":
            self.logger.debug(u"%s: Starting Oregon Scientific sensor device" % device.name)
            self.configOregon(device)
            self.sensorDevices[device.id] = device
               
        elif device.deviceTypeId == "rtsDevice":
            self.logger.debug(u"%s: Starting RTS device" % device.name)
            self.configRTS(device)
            self.sensorDevices[device.id] = device
               
        else:
            self.logger.error(u"%s: Unknown device type: %s in deviceStartComm" % (device.name, device.deviceTypeId))

        self.logger.debug(u"%s: Starting device completed, props = %s" % (device.name, device.pluginProps))

    
    def deviceStopComm(self, device):
        if device.deviceTypeId == "RFPlayer":
            self.logger.debug(u"%s: Stopping Interface device" % device.name)
            player = self.players[device.id]
            player.stop()
            del self.players[device.id]
        elif device.deviceTypeId == "x10Device":
            self.logger.debug(u"%s: Stopping X10 device" % device.name)
        elif device.deviceTypeId == "visonicDevice":
            self.logger.debug(u"%s: Stopping Visonic device" % device.name)
        elif device.deviceTypeId == "oregonDevice":
            self.logger.debug(u"%s: Stopping Oregon Scientific device" % device.name)
        else:
            self.logger.error("%s: Stopping unknown device type: %s" % (device.name, device.deviceTypeId))


    ########################################
    
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        if typeId == "x10Device":
            valuesDict['address'] = "X10-%s%s" % (valuesDict['houseCode'], valuesDict['unitCode'])
        return (True, valuesDict)

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        return
        
    def availableDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        retList =[]
        for address, data in sorted(self.knownDevices.iteritems()):
            if data['status'] == 'Available' and data['protocolMeaning'] == filter:
                retList.append((address, "%s: %s" % (address, data['description'])))
               
        retList.sort(key=lambda tup: tup[1])
        return retList

    ########################################

    def deviceDeleted(self, device):
        indigo.PluginBase.deviceDeleted(self, device)
        self.logger.debug(u"deviceDeleted: %s (%s)" % (device.name, device.id))

        if device.deviceTypeId == "RFPlayer":
            return

        self.logger.threaddebug(u"deviceDeleted (1) knownDevices = %s" % (str(self.knownDevices)))
            
        try:
            devices = self.knownDevices[device.address]['devices']
            devices.remove(device.id)
            self.knownDevices.setitem_in_item(device.address, 'devices', devices)
            if len(devices) == 0:
                self.knownDevices.setitem_in_item(device.address, 'status', "Available")
        except:
            pass
            
        self.logger.threaddebug(u"deviceDeleted (2) knownDevices = %s" % (str(self.knownDevices)))

    ########################################
    # Control Action callbacks
    ########################################
    
    def actionControlDevice(self, action, dev):
        ###### TURN ON ######
        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            # Command hardware module (dev) to turn ON here:
            # ** IMPLEMENT ME **
            sendSuccess = True      # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "on"))

                # And then tell the Indigo Server to update the state.
                dev.updateStateOnServer("onOffState", True)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "on"), isError=True)

        ###### TURN OFF ######
        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            # Command hardware module (dev) to turn OFF here:
            # ** IMPLEMENT ME **
            sendSuccess = True      # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "off"))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("onOffState", False)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "off"), isError=True)

        ###### TOGGLE ######
        elif action.deviceAction == indigo.kDeviceAction.Toggle:
            # Command hardware module (dev) to toggle here:
            # ** IMPLEMENT ME **
            newOnState = not dev.onState
            sendSuccess = True      # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "toggle"))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("onOffState", newOnState)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "toggle"), isError=True)

        ###### SET BRIGHTNESS ######
        elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
            # Command hardware module (dev) to set brightness here:
            # ** IMPLEMENT ME **
            newBrightness = action.actionValue
            sendSuccess = True      # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s to %d" % (dev.name, "set brightness", newBrightness))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("brightnessLevel", newBrightness)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s to %d failed" % (dev.name, "set brightness", newBrightness), isError=True)

        ###### BRIGHTEN BY ######
        elif action.deviceAction == indigo.kDeviceAction.BrightenBy:
            # Command hardware module (dev) to do a relative brighten here:
            # ** IMPLEMENT ME **
            newBrightness = dev.brightness + action.actionValue
            if newBrightness > 100:
                newBrightness = 100
            sendSuccess = True      # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s to %d" % (dev.name, "brighten", newBrightness))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("brightnessLevel", newBrightness)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s to %d failed" % (dev.name, "brighten", newBrightness), isError=True)

        ###### DIM BY ######
        elif action.deviceAction == indigo.kDeviceAction.DimBy:
            # Command hardware module (dev) to do a relative dim here:
            # ** IMPLEMENT ME **
            newBrightness = dev.brightness - action.actionValue
            if newBrightness < 0:
                newBrightness = 0
            sendSuccess = True      # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s to %d" % (dev.name, "dim", newBrightness))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("brightnessLevel", newBrightness)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s to %d failed" % (dev.name, "dim", newBrightness), isError=True)


    ########################################
    # General Action callbacks
    ########################################
    
    def actionControlUniversal(self, action, dev):
        ###### BEEP ######
        if action.deviceAction == indigo.kUniversalAction.Beep:
            # Beep the hardware module (dev) here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

        ###### ENERGY UPDATE ######
        elif action.deviceAction == indigo.kUniversalAction.EnergyUpdate:
            # Request hardware module (dev) for its most recent meter data here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy update request"))

        ###### ENERGY RESET ######
        elif action.deviceAction == indigo.kUniversalAction.EnergyReset:
            # Request that the hardware module (dev) reset its accumulative energy usage data here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy reset request"))

        ###### STATUS REQUEST ######
        elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
            # Query hardware module (dev) for its current status here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))


    ########################################
    # Plugin Actions object callbacks
    ########################################

    def validateActionConfigUi(self, valuesDict, typeId, devId):
        errorsDict = indigo.Dict()
        try:
            pass
        except:
            pass
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

    def sendCommandAction(self, pluginAction, playerDevice, callerWaitingForResult):

        player = self.players[playerDevice.id]
        command = indigo.activePlugin.substitute(pluginAction.props["textString"])

        try:
            self.logger.debug(u"sendCommandAction command '" + command + "' to " + playerDevice.name)
            player.sendRawCommand(command)
        except Exception, e:
            self.logger.exception(u"sendCommandAction error: %s" % str(e))

    def sendX10CommandAction(self, pluginAction, playerDevice, callerWaitingForResult):

        player = self.players[playerDevice.id]
        command = pluginAction.props["command"]
        houseCode = pluginAction.props["houseCode"]
        unitCode = pluginAction.props["unitCode"]

        if command == "DIM":
            brightness = pluginAction.props["brightness"]
            cmdString = "DIM %s%s X10 %%%s" % (houseCode, unitCode, brightness)
        else:
            cmdString = "%s %s%s X10" % (command, houseCode, unitCode)
        
        try:
            self.logger.debug(u"sendX10CommandAction command '" + cmdString + "' to " + playerDevice.name)
            player.sendRawCommand(cmdString)
        except Exception, e:
            self.logger.exception(u"sendX10CommandAction error: %s" % str(e))

    def setFrequencyAction(self, pluginAction, playerDevice, callerWaitingForResult):

        player = self.players[playerDevice.id]
        band = pluginAction.props["freqBand"]
        lowBand = pluginAction.props["lowBand"]
        highBand = pluginAction.props["highBand"]
        
        if band == "H":
            command = "FREQ H " + highBand
        elif band == "L":
            command = "FREQ L " + lowBand

        try:
            self.logger.debug(u"setFrequencyAction for %s, band = %s, lowBand = %s, highBand = %s " % (playerDevice.name, band, lowBand, highBand))
            player.sendRawCommand(command)
        except Exception, e:
            self.logger.exception(u"setFrequencyAction error: %s" % str(e))


    ########################################
    # Menu Methods
    ########################################

    def checkForUpdates(self):
        self.updater.checkForUpdate()

    def updatePlugin(self):
        self.updater.update()

    def forceUpdate(self):
        self.updater.update(currentVersion='0.0.0')

    def sendCommandMenu(self, valuesDict, typeId):
        try:
            deviceId = int(valuesDict["targetDevice"])
        except:
            self.logger.error(u"Bad Device specified for Send Command operation")
            return False

        try:
            textString = valuesDict["textString"]
        except:
            self.logger.error(u"Bad text string specified for Send Command operation")
            return False

        player = self.players[deviceId]
        command = indigo.activePlugin.substitute(textString)

        try:
            self.logger.debug(u"sendCommandMenu command '" + command + "' to " + indigo.devices[deviceId].name)
            player.sendRawCommand(command)
        except Exception, e:
            self.logger.exception(u"sendCommandMenu error: %s" % str(e))

        return True

    def pickPlayer(self, filter=None, valuesDict=None, typeId=0):
        retList = []
        for device in indigo.devices.iter("self"):
            if device.deviceTypeId == "RFPlayer":
                retList.append((device.id, device.name))
        retList.sort(key=lambda tup: tup[1])
        return retList

    def getRFBands(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        rfPlayer = indigo.devices[targetId]
        playerType = rfPlayer.pluginProps[u'playerModel']
        self.logger.debug(u"getRFBands for %s (%s)" % (rfPlayer.name, playerType))
        
        if playerType == "US":
            return [("H", "310/315MHz Band"), ("L", "433Mhz Band")]
        elif playerType == "EU":
            return [("H", "868MHz Band"), ("L", "433Mhz Band")]
        
        self.logger.error(u"Unknown playerType = %s in getRFBands" % (playerType))     
        return None

    def getHighBands(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        rfPlayer = indigo.devices[targetId]
        playerType = rfPlayer.pluginProps[u'playerModel']
        self.logger.debug(u"getHighBands for %s (%s)" % (rfPlayer.name, playerType))
        
        if playerType == "US":
            return [("0", "Off"), ("310000", "310MHz"), ("315000", "315MHz")]
        elif playerType == "EU":
            return [("0", "Off"), ("868350", "868.350MHz"), ("868950", "868.950MHz")]
        
        self.logger.error(u"Unknown playerType = %s in getHighBands" % (playerType))     
        return None

    def getLowBands(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        rfPlayer = indigo.devices[targetId]
        playerType = rfPlayer.pluginProps[u'playerModel']
        self.logger.debug(u"getLowBands for %s (%s)" % (rfPlayer.name, playerType))

        if playerType == "US":
            return [("0", "Off"), ("433420", "433.420Mhz"), ("433920", "433.920Mhz")]
        elif playerType == "EU":
            return [("0", "Off"), ("433420", "433.420Mhz"), ("433920", "433.920Mhz")]
        
        self.logger.error(u"Unknown playerType = %s in getLowBands" % (playerType))     
        return None


    ########################################
    # Protocol Specific Methods
    ########################################

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

    ########################################

    def visonicHandler(self, player, frameData):

        devAddress = "VISONIC-" + frameData['infos']['id']

        self.logger.debug(u"%s: Visonic frame received: %s" % (player.device.name, devAddress))

        # make sure this device is in the list of known sensor devices
        
        if devAddress not in self.knownDevices:
            self.logger.info("New Visonic Device %s" % (devAddress))
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
       

    ########################################

    def blyssHandler(self, player, frameData):

        devAddress = "BLYSS-" + frameData['infos']['id']

        self.logger.debug(u"%s: Sensor Blyss received: %s" % (player.device.name, devAddress))

    ########################################

    def chaconHandler(self, player, frameData):

        devAddress = "CHACON-" + frameData['infos']['id']

        self.logger.debug(u"%s: Chacon frame received: %s" % (player.device.name, devAddress))

    ########################################

    def oregonHandler(self, player, frameData):

        devAddress = "OREGON-" + frameData['infos']['adr_channel']

        self.logger.debug(u"%s: Oregon frame received: %s" % (player.device.name, devAddress))
        
        # make sure this device is in the list of known sensor devices
        
        if devAddress not in self.knownDevices:
            self.logger.info("New Oregon Device %s - %s (%s)" % (devAddress, frameData['infos']['id_PHYMeaning'], frameData['infos']['id_PHY']))
            self.knownDevices[devAddress] = { 
                "status": "Available", 
                "devices" : indigo.List(),
                "protocol": frameData['header']['protocol'], 
                "protocolMeaning": frameData['header']['protocolMeaning'], 
                "infoType": frameData['header']['infoType'], 
                "subType": frameData['infos']['id_PHY'],
                "description": frameData['infos']['id_PHYMeaning'],
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
                        valueString = "%.1f °C" % value
                    else:
                        value = 9.0/5.0 * float(rawValue) + 32.0
                        valueString = "%.1f °F" % value
                
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
       
    ########################################

    def domiaHandler(self, player, frameData):

        devAddress = "DOMIA-" + frameData['infos']['idMeaning']

        self.logger.debug(u"%s: Domia frame received: %s" % (player.device.name, devAddress))

        # make sure this device is in the list of known sensor devices
        
        if devAddress not in self.knownDevices:
            self.logger.info("New Domia Device %s" % (devAddress))
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
            sensor.updateStateOnServer('onOffState', bool(int(sensorState)))
            sensor.updateStateOnServer('sensorValue', sensorState, uiValue=sensorState)

    def configDomia(self, device):

        configDone = device.pluginProps.get('configDone', False)
        self.logger.debug(u" %s: configDomia, configDone = %s" % (device.name, str(configDone)))
        
        if configDone:
            return

        address = device.pluginProps['address']

        self.logger.threaddebug(u"configDomia (1) for knownDevices[%s] = %s" % (address, str(self.knownDevices[address])))

        self.knownDevices.setitem_in_item(address, 'status', "Active")
        devices = self.knownDevices[address]['devices']
        devices.append(device.id)
        self.knownDevices.setitem_in_item(address, 'devices', devices)

        self.logger.threaddebug(u"configDomia (2) for knownDevices[%s] = %s" % (address, str(self.knownDevices[address])))
        
        
        device.name = address
        device.replaceOnServer()

        newProps = device.pluginProps
        newProps["configDone"] = True
        device.replacePluginPropsOnServer(newProps)

        self.logger.info(u"Configured configDomia Sensor '%s' (%s) @ %s" % (device.name, device.id, address))
       
    ########################################

    def owlHandler(self, player, frameData):

        devAddress = "OWL-" + frameData['infos']['id']

        self.logger.debug(u"%s: Owl frame received: %s" % (player.device.name, devAddress))

    ########################################

    def x2dHandler(self, player, frameData):

        devAddress = "X2D-" + frameData['infos']['id']

        self.logger.debug(u"%s: X2D frame received: %s" % (player.device.name, devAddress))

    ########################################

    def rtsHandler(self, player, frameData):

        devAddress = "RTS-" + frameData['infos']['id']

        self.logger.debug(u"%s: RTS frame received: %s" % (player.device.name, devAddress))
    
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
    ########################################

    def kd101Handler(self, player, frameData):

        devAddress = "KD101-" + frameData['infos']['id']

        self.logger.debug(u"%s: KD101 frame received: %s" % (player.device.name, devAddress))

    ########################################

    def parrotHandler(self, player, frameData):

        devAddress = "PARROT-" + frameData['infos']['idMeaning']

        self.logger.debug(u"%s: Parrot frame received: %s" % (player.device.name, devAddress))
        
        
