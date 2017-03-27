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
        self.logger.debug(u"logLevel = " + str(self.logLevel))

    def startup(self):
        self.logger.info(u"Starting RFPlayer")

        self.players = { }
        self.triggers = { }

        self.updater = GitHubPluginUpdater(self)
        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
        self.logger.debug(u"updateFrequency = " + str(self.updateFrequency))
        self.next_update_check = time.time()

    def shutdown(self):
        self.logger.info(u"Shutting down RFPlayer")


    def runConcurrentThread(self):

        try:
            while True:

                for playerID, player in self.players.items():
                    playerFrame = player.poll()
                    if playerFrame:
                        self.frameHandler(player, playerFrame)
    
                if (self.updateFrequency > 0.0) and (time.time() > self.next_update_check):
                    self.next_update_check = time.time() + self.updateFrequency
                    self.updater.checkForUpdate()

                self.sleep(0.1)

        except self.stopThread:
            for playerID, player in self.players.items():
                player.stop()

    def frameHandler(self, player, playerFrame):
    
        if 'systemStatus' in playerFrame:
            self.logger.debug(u"u'parrotStatus received, reqNum = %s" % playerFrame['systemStatus']['reqNum'])
            for info in playerFrame['systemStatus']['info']:
                if 'n' in info:
                    self.logger.debug(u"\t%s = %s" % (info['n'], info['v']))
                if 'transmitter' in info:
                    self.logger.debug(u"\tTransmitter Protocols = %s" % (info['transmitter']['available']['p']))
                if 'receiver' in info:
                    if 'available' in info['receiver']:                
                        self.logger.debug(u"\tAvailable Receiver Protocols = %s" % (info['receiver']['available']['p']))
                    if 'enabled' in info['receiver']:                
                        self.logger.debug(u"\tEnabled Receiver Protocols = %s" % (info['receiver']['enabled']['p']))
                if 'repeater' in info:
                    if 'available' in info['repeater']:                
                        self.logger.debug(u"\tAvailable Repeater Protocols = %s" % (info['repeater']['available']['p']))
                    if 'enabled' in info['repeater']:                
                        self.logger.debug(u"\tEnabled Repeater Protocols = %s" % (info['repeater']['enabled']['p']))
                    
        elif 'radioStatus' in playerFrame:
            self.logger.debug(u"u'parrotStatus received, reqNum = %s" % playerFrame['radioStatus']['reqNum'])
            for band in playerFrame['radioStatus']['band']:
                if 'i' in band:
                    for info in band['i']:
                        if 'n' in info:
                            self.logger.debug(u"\t%s = %s%s (%s)" % (info['n'], info['v'], info['unit'], info['c'].strip()))
               
        elif 'parrotStatus' in playerFrame:
            self.logger.debug(u"u'parrotStatus received, reqNum = %s" % playerFrame['parrotStatus']['reqNum'])
            for info in playerFrame['parrotStatus']['info']:
                if 'n' in info:
                    self.logger.debug(u"\t%s = %s (%s), " % (info['n'], info['v'], str(info)))
               
        elif 'transcoderStatus' in playerFrame:
            self.logger.debug(u"u'transcoderStatus received, reqNum = %s" % playerFrame['transcoderStatus']['reqNum'])
            for info in playerFrame['transcoderStatus']['info']:
                if 'n' in info:
                    self.logger.debug(u"\t%s = %s (%s), " % (info['n'], info['v'], str(info)))
               
        else:
            self.logger.debug(u"Unknown playerFrame:\n" + str(playerFrame))        
            

    ####################

    def triggerStartProcessing(self, trigger):
        self.logger.debug("Adding Trigger %s (%d) - %s" % (trigger.name, trigger.id, trigger.pluginTypeId))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.logger.debug("Removing Trigger %s (%d)" % (trigger.name, trigger.id))
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

    def triggerCheck(self, device):

        for triggerId, trigger in sorted(self.triggers.iteritems()):
            self.logger.debug("Checking Trigger %s (%s), Type: %s" % (trigger.name, trigger.id, trigger.pluginTypeId))

#           if (trigger.pluginProps["twilioNumber"] != str(device.id)) and (trigger.pluginProps["twilioNumber"] != kAnyDevice):
#               self.logger.debug("\tSkipping Trigger %s (%s), wrong device: %s" % (trigger.name, trigger.id, device.id))

#           if trigger.pluginTypeId == "messageReceived":
#               indigo.trigger.execute(trigger)

#           else:
#               self.logger.warning("\tUnknown Trigger Type %s (%d), %s" % (trigger.name, trigger.id, trigger.pluginTypeId))



    ####################
    def validatePrefsConfigUi(self, valuesDict):
        self.logger.debug(u"validatePrefsConfigUi called")
        errorDict = indigo.Dict()

        updateFrequency = int(valuesDict['updateFrequency'])
        if (updateFrequency < 0) or (updateFrequency > 24):
            errorDict['updateFrequency'] = u"Update frequency is invalid - enter a valid number (between 0 and 24)"

        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)
        return (True, valuesDict)

    ########################################
    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            try:
                self.logLevel = int(valuesDict[u"logLevel"])
            except:
                self.logLevel = logging.INFO
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"logLevel = " + str(self.logLevel))

            self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
            self.logger.debug(u"updateFrequency = " + str(self.updateFrequency))
            self.next_update_check = time.time()


    ########################################
    # Called for each enabled Device belonging to plugin
    #
    def deviceStartComm(self, device):
        self.logger.debug(u'Called deviceStartComm(self, device): %s (%s)' % (device.name, device.id))

        instanceVers = int(device.pluginProps.get('devVersCount', 0))
        self.logger.debug(device.name + u": Device Current Version = " + str(instanceVers))

        if instanceVers >= kCurDevVersCount:
            newProps = device.pluginProps

            newProps["devVersCount"] = kCurDevVersCount
            device.replacePluginPropsOnServer(newProps)
            device.stateListOrDisplayStateIdChanged()
            self.logger.debug(u"Updated " + device.name + " to version " + str(kCurDevVersCount))

        elif instanceVers < kCurDevVersCount:
            newProps = device.pluginProps

        else:
            self.logger.warning(u"Unknown device version: " + str(instanceVers) + " for device " + device.name)

        if device.deviceTypeId == "RFPlayer":
            if device.id not in self.players:
                self.logger.debug(u"Starting interface device %s" % device.name)
                serialPort = device.pluginProps.get(u'serialPort', "")
                baudRate = int(device.pluginProps.get(u'baudRate', 0))

                player = RFPlayer(self)
                player.start(serialPort, baudRate)
                self.players[device.id] = player
            else:
                self.logger.debug(u"Duplicate Device ID: " + device.name)
        else:
            self.logger.error("Unknown device type: %s" % device.deviceTypeId)

    ########################################
    # Terminate communication with servers
    #
    def deviceStopComm(self, device):
        self.logger.debug(u'Called deviceStopComm(self, device): %s (%s)' % (device.name, device.id))
        player = self.players[device.id]
        player.stop()
        del self.players[device.id]


    ########################################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        errorsDict = indigo.Dict()
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        return (True, valuesDict)

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

    ########################################
    # Plugin Actions object callbacks
    ########################################

    def sendCommandAction(self, pluginAction, playerDevice, callerWaitingForResult):

        player = self.players[playerDevice.id]
        command = indigo.activePlugin.substitute(pluginAction.props["textString"])

        try:
            self.logger.debug(u"sendCommandAction command '" + command + "' to " + playerDevice.name)
            player.sendCommand(command)
        except Exception, e:
            self.logger.exception(u"sendCommandAction error: %s" % str(e))

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

    def sendHelloMenu(self, valuesDict, typeId):
        try:
            deviceId = int(valuesDict["targetDevice"])
        except:
            self.logger.error(u"Bad Device specified for Send Hello operation")
            return False

        for playerID, player in self.players.items():
            if playerID == deviceId:
                player.sendRawCommand("HELLO")

        return True

    def sendStatusMenu(self, valuesDict, typeId):
        try:
            deviceId = int(valuesDict["targetDevice"])
        except:
            self.logger.error(u"Bad Device specified for Send Status operation")
            return False

        for playerID, player in self.players.items():
            if playerID == deviceId:
                player.sendCommand("STATUS")

        return True


    def pickPlayer(self, filter=None, valuesDict=None, typeId=0):
        retList = []
        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == "RFPlayer":
                retList.append((dev.id, dev.name))
        retList.sort(key=lambda tup: tup[1])
        return retList

