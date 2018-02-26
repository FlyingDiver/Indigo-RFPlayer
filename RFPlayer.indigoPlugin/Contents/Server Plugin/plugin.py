#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys
import time
from datetime import datetime
import logging

from ghpu import GitHubPluginUpdater

from RFPlayer import RFPlayer

import protocols

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

        
        
