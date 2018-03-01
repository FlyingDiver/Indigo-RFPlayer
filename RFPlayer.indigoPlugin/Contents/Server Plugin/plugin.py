#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys
import time
from datetime import datetime
import json
import logging

from ghpu import GitHubPluginUpdater

from RFPlayer import RFPlayer
from protocols import Blyss, Chacon, Domia, KD101, Oregon, Owl, Parrot, RTS, Visonic, X2D, X10

kCurDevVersCount = 0        # current version of plugin devices

################################################################################
class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        try:
            self.logLevel = int(self.pluginPrefs[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)

    def startup(self):
        self.logger.info(u"Starting RFPlayer")

        self.players = { }
        self.sensorDevices = {}
        self.knownDevices = indigo.activePlugin.pluginPrefs.get(u"knownDevices", indigo.Dict())
        
        self.protocolClasses = {
            "1"  : X10,
            "2"  : Visonic,
            "3"  : Blyss,
            "4"  : Chacon,
            "5"  : Oregon,
            "6"  : Domia,
            "7"  : Owl,
            "8"  : X2D,
            "9"  : RTS,
            "10" : KD101,
            "11" : Parrot
        }
        
        self.deviceTypeClasses = {
            "x10Device"     : X10,
            "visonicDevice" : Visonic,
            "blyssDevice"   : Blyss,
            "chaconDevice"  : Chacon,
            "oregonDevice"  : Oregon,
            "domiaDevice"   : Domia,
            "owlDevice"     : Owl,
            "x2dDevice"     : X2D,
            "rtsDevice"     : RTS,
            "kd101Device"   : KD101,
            "parrotDevice"  : Parrot
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
                            self.logger.threaddebug(u"%s: systemStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
                    
                        elif 'radioStatus' in playerFrame:
                            self.logger.debug(u"%s: radioStatus received" % (player.device.name))
                            self.logger.threaddebug(u"%s: radioStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
               
                        elif 'parrotStatus' in playerFrame:
                            self.logger.debug(u"%s: parrotStatus received" % (player.device.name))
                            self.logger.threaddebug(u"%s: parrotStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
               
                        elif 'transcoderStatus' in playerFrame:
                            self.logger.debug(u"%s: transcoderStatus received" % (player.device.name))
                            self.logger.threaddebug(u"%s: transcoderStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
               
                        elif 'frame' in playerFrame:    # async frame.  Find a device to handle it
            
                            try:
                                protocol = playerFrame['frame']['header']['protocol']
                                if protocol in self.protocolClasses:
                                    devAddress = self.protocolClasses[protocol].frameCheck(player.device, playerFrame['frame'], self.knownDevices)
                                    
                                    if devAddress in self.sensorDevices:
                                        self.sensorDevices[devAddress].handler(player, playerFrame['frame'], self.knownDevices)

                                    else:
                                        self.logger.threaddebug("%s: Frame from %s, known and not configured.  Ignoring." % (player.device.name, devAddress))

                                else:
                                    self.logger.error(u"%s: Unknown protocol:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      

                            except Exception, e:
                                self.logger.debug(u"%s: Frame decode error:%s\n%s" %  (player.device.name, str(e), json.dumps(playerFrame, indent=4, sort_keys=True)))      
                                
            
                        else:
                            self.logger.error(u"%s: Unknown playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
    
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
            self.logger.debug(u"RFPlayer logLevel = " + str(self.logLevel))

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

        
        if device.deviceTypeId == "RFPlayer":
            serialPort = device.pluginProps.get(u'serialPort', "")
            baudRate = int(device.pluginProps.get(u'baudRate', 0))
            player = RFPlayer(self, device)
            player.start(serialPort, baudRate)
            self.players[device.id] = player
        
        else:
            address = device.pluginProps.get(u'address', "")
            self.sensorDevices[address] = (self.deviceTypeClasses[device.deviceTypeId])(device, self.knownDevices)
        
        self.logger.debug(u"%s: deviceStartComm complete, sensorDevices[] =" % (device.name))
        for key, sensor in self.sensorDevices.iteritems():
            self.logger.debug(u"\tkey = %s, sensor.name = %s, sensor.id = %d" % (key, sensor.device.name, sensor.device.id))
            
    
    def deviceStopComm(self, device):
        if device.deviceTypeId == "RFPlayer":
            self.logger.debug(u"%s: Stopping Interface device" % device.name)
            player = self.players[device.id]
            player.stop()
            del self.players[device.id]
        else:
            self.logger.debug(u"%s: Stopping sensor device" % device.name)
            address = device.pluginProps.get(u'address', "")
            try:
                del self.sensorDevices[address]
            except:
                pass
#                self.logger.error(u"%s: Unregistered sensor device @ %s" % (device.name, address))
            

    ########################################
    
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        if typeId == "x10Device":
            valuesDict['address'] = "X10-%s%s" % (valuesDict['houseCode'], valuesDict['unitCode'])
        elif typeId == "parrotDevice":
            valuesDict['address'] = "PARROT-%s%s" % (valuesDict['houseCode'], valuesDict['unitCode'])
        return (True, valuesDict)

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        return
        
    def availableDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        retList =[]
        for address, data in sorted(self.knownDevices.iteritems()):
            if data['status'] == 'Available' and data['protocol'] == filter:
                retList.append((address, "%s: %s" % (address, data['description'])))
               
        retList.sort(key=lambda tup: tup[1])
        return retList

    ########################################

    def deviceDeleted(self, device):
        indigo.PluginBase.deviceDeleted(self, device)

        try:
            devices = self.knownDevices[device.address]['devices']
            devices.remove(device.id)
            self.knownDevices.setitem_in_item(device.address, 'devices', devices)
            self.knownDevices.setitem_in_item(device.address, 'status', "Available")
            self.logger.debug(u"deviceDeleted: %s (%s)" % (device.name, device.id))
        except:
            pass
            
    ########################################
    # Control Action callbacks
    ########################################
    
    def actionControlUniversal(self, action, dev):
        if action.deviceAction == indigo.kUniversalAction.RequestStatus:
            sensor = self.sensorDevices[dev.address]
            player = self.players[sensor.player.id]
            sensor.requestStatus(player)

    def actionControlDevice(self, action, dev):
        sensor = self.sensorDevices[dev.address]
        player = self.players[sensor.player.id]
        
        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            sendSuccess = sensor.turnOn(player)
            if sendSuccess:
                dev.updateStateOnServer("onOffState", True)
            else:
                self.logger.error(u"send \"%s\" %s failed" % (dev.name, "On"))

        ###### TURN OFF ######
        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            sendSuccess = sensor.turnOff(player)
            if sendSuccess:
                dev.updateStateOnServer("onOffState", False)
            else:
                self.logger.error(u"send \"%s\" %s failed" % (dev.name, "Off"))
                


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

    # doesn't do anything, just needed to force other menus to dynamically refresh
    def menuChanged(self, valuesDict, typeId, devId):
        return valuesDict

    def checkForUpdates(self):
        self.updater.checkForUpdate()

    def updatePlugin(self):
        self.updater.update()

    def forceUpdate(self):
        self.updater.update(currentVersion='0.0.0')

    def dumpKnownDevices(self):
        self.logger.info(u"Known device list:\n" + str(self.knownDevices))
        
    def purgeKnownDevices(self):
        self.logger.info(u"Purging Known device list...")
        for address, data in self.knownDevices.iteritems():
            if data['status'] == 'Available':
                self.logger.info(u"\t%s" % (address))       
                del self.knownDevices[address]

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

    def pickPlayer(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        retList = []
        for device in indigo.devices.iter("self"):
            if device.deviceTypeId == "RFPlayer":
                retList.append((device.id, device.name))
        retList.sort(key=lambda tup: tup[1])
        return retList

    def pickPlayerDevice(self, filter=None, valuesDict=None, typeId=0, targetId=0):
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
            return [("0", "Off"), ("310000", "310MHz - X10 RF"), ("315000", "315MHz - Visonic")]
        elif playerType == "EU":
            return [("0", "Off"), ("868350", "868.350MHz"), ("868950", "868.950MHz")]
        
        self.logger.error(u"Unknown playerType = %s in getHighBands" % (playerType))     
        return None

    def getLowBands(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        rfPlayer = indigo.devices[targetId]
        playerType = rfPlayer.pluginProps[u'playerModel']
        self.logger.debug(u"getLowBands for %s (%s)" % (rfPlayer.name, playerType))

        if playerType == "US":
            return [("0", "Off"), ("433420", "433.420Mhz - Somfy RTS"), ("433920", "433.920Mhz - Most 433MHz devices")]
        elif playerType == "EU":
            return [("0", "Off"), ("433420", "433.420Mhz"), ("433920", "433.920Mhz")]
        
        self.logger.error(u"Unknown playerType = %s in getLowBands" % (playerType))     
        return None

        
        
