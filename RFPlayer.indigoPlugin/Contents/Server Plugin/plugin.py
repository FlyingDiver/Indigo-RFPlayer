#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys
import time
from datetime import datetime
import json
import logging

from RFPlayer import RFPlayer
from protocols import Blyss, Chacon, Domia, KD101, Oregon, Owl, Parrot, RTS, Visonic, X2D, X10

kCurDevVersCount = 2        # current version of plugin devices

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
        self.triggers = {}
       
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
        
    def shutdown(self):
        indigo.activePlugin.pluginPrefs[u"knownDevices"] = self.knownDevices
        self.logger.info(u"Shutting down RFPlayer")


    def runConcurrentThread(self):

        try:
            while True:

                for playerID, player in self.players.items():
                    if player.connected:
                        playerFrame = player.poll()     
                    
                    if playerFrame:
                        indigo.devices[playerID].updateStateOnServer(key='playerStatus', value='Running')
                        if 'systemStatus' in playerFrame:
                            self.logger.debug(u"%s: systemStatus frame received" % (player.device.name))
                            self.logger.threaddebug(u"%s: systemStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
                            stateList = [
                                { 'key':'firmwareVers', 'value':playerFrame[u'systemStatus'][u'info'][0][u'v'] }
                            ]
                            self.logger.threaddebug(u'%s: Updating states on server: %s' % (player.device.name, str(stateList)))
                            indigo.devices[playerID].updateStatesOnServer(stateList)
                    
                        elif 'radioStatus' in playerFrame:
                            self.logger.debug(u"%s: radioStatus frame received" % (player.device.name))
                            self.logger.threaddebug(u"%s: radioStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
                            stateList = [
                                { 'key':'lowBandFreq',   
                                'value':playerFrame[u'radioStatus'][u'band'][0][u'i'][0][u'v']+' - '+ playerFrame[u'radioStatus'][u'band'][0][u'i'][0][u'c'] },
                                { 'key':'highBandFreq',
                                'value':playerFrame[u'radioStatus'][u'band'][1][u'i'][0][u'v']+' - '+ playerFrame[u'radioStatus'][u'band'][1][u'i'][0][u'c'] }
                            ]
                            self.logger.threaddebug(u'%s: Updating states on server: %s' % (player.device.name, str(stateList)))
                            indigo.devices[playerID].updateStatesOnServer(stateList)
               
                        elif 'parrotStatus' in playerFrame:
                            self.logger.debug(u"%s: parrotStatus frame received" % (player.device.name))
                            self.logger.threaddebug(u"%s: parrotStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
               
                        elif 'transcoderStatus' in playerFrame:
                            self.logger.debug(u"%s: transcoderStatus frame received" % (player.device.name))
                            self.logger.threaddebug(u"%s: transcoderStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
               
                        elif 'alarmStatus' in playerFrame:
                            self.logger.debug(u"%s: alarmStatus frame received" % (player.device.name))
                            self.logger.threaddebug(u"%s: alarmStatus playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
               
                        elif 'frame' in playerFrame:    # async frame.  Find a device to handle it
            
                            try:
                                protocol = playerFrame['frame']['header']['protocol']
                                if protocol in self.protocolClasses:
                                    devAddress = self.protocolClasses[protocol].frameCheck(player.device, playerFrame['frame'], self.knownDevices)
                                    
                                    if devAddress in self.sensorDevices:
                                        self.sensorDevices[devAddress].handler(playerFrame['frame'], self.knownDevices)

                                    else:
                                        self.logger.threaddebug("%s: Frame from %s, known and not configured.  Ignoring." % (player.device.name, devAddress))

                                else:
                                    self.logger.error(u"%s: Unknown protocol:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      

                            except Exception, e:
                                self.logger.debug(u"%s: Frame decode error:%s\n%s" %  (player.device.name, str(e), json.dumps(playerFrame, indent=4, sort_keys=True)))      
                                
            
                        else:
                            self.logger.error(u"%s: Unknown playerFrame:\n%s" %  (player.device.name, json.dumps(playerFrame, indent=4, sort_keys=True)))      
    
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


    ########################################
    # Device Management Methods
    ########################################

    def didDeviceCommPropertyChange(self, origDev, newDev):
    
        if newDev.deviceTypeId == "RFPlayer":
            if origDev.pluginProps.get('serialPort', None) != newDev.pluginProps.get('serialPort', None):
                return True           

        return False
      
    def deviceStartComm(self, device):

        self.logger.debug(u"%s: Starting Device" % device.name)

        instanceVers = int(device.pluginProps.get('devVersCount', 0))
        if instanceVers == kCurDevVersCount:
            self.logger.threaddebug(u"%s: Device is current version: %d" % (device.name ,instanceVers))
        elif instanceVers < kCurDevVersCount:
            newProps = device.pluginProps
            newProps["devVersCount"] = kCurDevVersCount
            device.replacePluginPropsOnServer(newProps)
            self.logger.debug(u"%s: Updated device version: %d -> %d" % (device.name,  instanceVers, kCurDevVersCount))
        else:
            self.logger.warning(u"%s: Invalid device version: %d" % (device.name, instanceVers))
        
        self.logger.threaddebug(u"%s: Starting Device: %s" % (device.name , unicode(device)))

        if device.deviceTypeId == "RFPlayer":
            serialPort = device.pluginProps.get(u'serialPort', "")
            baudRate = int(device.pluginProps.get(u'baudRate', 0))
            player = RFPlayer(self, device)
            player.start(serialPort, baudRate)
            self.players[device.id] = player
            device.updateStateOnServer(key='playerStatus', value='Starting')
        
        else:
            address = device.pluginProps.get(u'address', "")
            protocol = self.knownDevices[address]['protocol']
            self.sensorDevices[address] = (self.protocolClasses[protocol])(device, self.knownDevices)
        
        self.logger.debug(u"%s: deviceStartComm complete, sensorDevices[] =" % (device.name))
        for key, sensor in self.sensorDevices.iteritems():
            self.logger.debug(u"\tkey = %s, sensor.name = %s, sensor.id = %d" % (key, sensor.device.name, sensor.device.id))
            
    
    def deviceStopComm(self, device):
        self.logger.debug(u"%s: Stopping Device" % device.name)
        if device.deviceTypeId == "RFPlayer":
            device.updateStateOnServer(key='playerStatus', value='Stopping')
            player = self.players[device.id]
            player.stop()
            del self.players[device.id]
        else:
            address = device.pluginProps.get(u'address', "")
            try:
                del self.sensorDevices[address]
            except:
                pass
            

    ########################################
    
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        if typeId == "x10Device":
            valuesDict['address'] = "X10-%s%s" % (valuesDict['houseCode'], valuesDict['unitCode'])
        elif typeId == "parrotDevice":
            valuesDict['address'] = "PARROT-%s%s" % (valuesDict['houseCode'], valuesDict['unitCode'])
        return (True, valuesDict)

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        return
        
    # return a list of all "Available" devices (not associated with an Indigo device)
    
    def availableDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        retList =[]
        for address, data in sorted(self.knownDevices.iteritems()):
            if data['status'] == 'Available':
                retList.append((address, "%s: %s" % (address, data['description'])))
               
        retList.sort(key=lambda tup: tup[1])
        return retList

    # return a list of all "Active" devices of a specific type

    def activeDeviceList(self, filter="", valuesDict=None, typeId="discoveredDevice", targetId=0):
        retList =[]
        for address, data in sorted(self.knownDevices.iteritems()):
            if data['status'] == 'Active' and (filter in address) :
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
            
    def triggerStartProcessing(self, trigger):
        self.logger.debug("Adding Trigger %s (%d)" % (trigger.name, trigger.id))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.logger.debug("Removing Trigger %s (%d)" % (trigger.name, trigger.id))
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

    def triggerCheck(self, device):
        self.logger.threaddebug("Checking Triggers for Device %s (%d)" % (device.name, device.id))

        for triggerId, trigger in sorted(self.triggers.iteritems()):
            self.logger.threaddebug("\tChecking Trigger %s (%d), %s" % (trigger.name, trigger.id, trigger.pluginTypeId))

            if trigger.pluginProps["sensorID"] != str(device.id):
                self.logger.threaddebug("\t\tSkipping Trigger %s (%s), wrong device: %s" % (trigger.name, trigger.id, device.id))
            else:
                if trigger.pluginTypeId == "sensorFault":
                    if device.states["faultCode"]:          # trigger if faultCode is not None
                        self.logger.debug("Executing Trigger %s (%s)" % (trigger.name, trigger.id))
                        indigo.trigger.execute(trigger)
                    else:
                        self.logger.debug("\tNo Match for Trigger %s (%d)" % (trigger.name, trigger.id))
                else:
                    self.logger.threaddebug(
                        "\tUnknown Trigger Type %s (%d), %s" % (trigger.name, trigger.id, trigger.pluginTypeId))

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

    def sendRTSMyCommand(self, pluginAction, sensorDevice, callerWaitingForResult):

        sensorDevice = pluginAction.props["device"]
        sensor = self.sensorDevices[sensorDevice]
        player = self.players[sensor.player.id]
        try:
            self.logger.debug(u"sendRTSMyCommand to %s via %s" % (sensorDevice, player.device.name))
            player.sendMyCommand()
        except Exception, e:
            self.logger.exception(u"sendRTSMyCommand error: %s" % str(e))

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
            player.sendRawCommand("STATUS RADIO JSON")
        except Exception, e:
            self.logger.exception(u"setFrequencyAction error: %s" % str(e))


    ########################################
    # Menu Methods
    ########################################

    # doesn't do anything, just needed to force other menus to dynamically refresh
    def menuChanged(self, valuesDict, typeId, devId):
        return valuesDict

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

    def pickSensor(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        retList = []
        for device in indigo.devices.iter("self"):
            if device.deviceTypeId != "RFPlayer":
                retList.append((device.id, device.name))
        retList.sort(key=lambda tup: tup[1])
        return retList

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

        
        
