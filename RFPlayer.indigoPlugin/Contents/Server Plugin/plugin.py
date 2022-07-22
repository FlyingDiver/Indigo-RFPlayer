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

kCurDevVersCount = 2  # current version of plugin devices


################################################################################
class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        self.logLevel = int(self.pluginPrefs.get("logLevel", logging.INFO))
        self.indigo_log_handler.setLevel(self.logLevel)

        self.players = {}
        self.sensorDevices = {}
        self.knownDevices = pluginPrefs.get("knownDevices", indigo.Dict())
        self.triggers = {}

        self.protocolClasses = {
            "1": X10,
            "2": Visonic,
            "3": Blyss,
            "4": Chacon,
            "5": Oregon,
            "6": Domia,
            "7": Owl,
            "8": X2D,
            "9": RTS,
            "10": KD101,
            "11": Parrot
        }

    def startup(self):
        self.logger.info("Starting RFPlayer")

    def shutdown(self):
        indigo.activePlugin.pluginPrefs["knownDevices"] = self.knownDevices
        self.logger.info("Shutting down RFPlayer")

    def runConcurrentThread(self):

        try:
            while True:
                for playerID, player in self.players.items():
                    if player.connected:
                        playerFrame = player.poll()
                    else:
                        playerFrame = None

                    if playerFrame:
                        indigo.devices[playerID].updateStateOnServer(key='playerStatus', value='Running')
                        indigo.devices[playerID].updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                        if 'systemStatus' in playerFrame:
                            self.logger.debug(f"{player.device.name}: systemStatus frame received")
                            self.logger.threaddebug(
                                f"{player.device.name}: systemStatus playerFrame:\n{json.dumps(playerFrame, indent=4, sort_keys=True)}")
                            stateList = [
                                {'key': 'firmwareVers', 'value': playerFrame['systemStatus']['info'][0]['v']}
                            ]
                            self.logger.threaddebug(f'{player.device.name}: Updating states on server: {stateList}')
                            indigo.devices[playerID].updateStatesOnServer(stateList)

                        elif 'radioStatus' in playerFrame:
                            self.logger.debug(f"{player.device.name}: radioStatus frame received")
                            self.logger.threaddebug(
                                f"{player.device.name}: radioStatus playerFrame:\n{json.dumps(playerFrame, indent=4, sort_keys=True)}")
                            stateList = [
                                {'key': 'lowBandFreq',
                                 'value': playerFrame['radioStatus']['band'][0]['i'][0]['v'] + ' - ' + playerFrame['radioStatus']['band'][0]['i'][0][
                                     'c']},
                                {'key': 'highBandFreq',
                                 'value': playerFrame['radioStatus']['band'][1]['i'][0]['v'] + ' - ' + playerFrame['radioStatus']['band'][1]['i'][0][
                                     'c']}
                            ]
                            self.logger.threaddebug(f'{player.device.name}: Updating states on server: {stateList}')
                            indigo.devices[playerID].updateStatesOnServer(stateList)

                        elif 'parrotStatus' in playerFrame:
                            self.logger.debug(f"{player.device.name}: parrotStatus frame received")
                            self.logger.threaddebug(
                                f"{player.device.name}: parrotStatus playerFrame:\n{json.dumps(playerFrame, indent=4, sort_keys=True)}")

                        elif 'transcoderStatus' in playerFrame:
                            self.logger.debug(f"{player.device.name}: transcoderStatus frame received")
                            self.logger.threaddebug(
                                f"{player.device.name}: transcoderStatus playerFrame:\n{json.dumps(playerFrame, indent=4, sort_keys=True)}")

                        elif 'alarmStatus' in playerFrame:
                            self.logger.debug(f"{player.device.name}: alarmStatus frame received")
                            self.logger.threaddebug(
                                f"{player.device.name}: alarmStatus playerFrame:\n{json.dumps(playerFrame, indent=4, sort_keys=True)}")

                        elif 'frame' in playerFrame:  # async frame.  Find a device to handle it

                            try:
                                protocol = playerFrame['frame']['header']['protocol']
                                if protocol in self.protocolClasses:
                                    devAddress = self.protocolClasses[protocol].frameCheck(player.device, playerFrame['frame'], self.knownDevices)

                                    if devAddress in self.sensorDevices:
                                        self.sensorDevices[devAddress].handler(playerFrame['frame'], self.knownDevices)

                                    else:
                                        self.logger.threaddebug(
                                            f"{player.device.name}: Frame from {devAddress}, known and not configured.  Ignoring.")

                                else:
                                    self.logger.debug(f"{player.device.name}: Unknown protocol:\n{json.dumps(playerFrame, indent=4, sort_keys=True)}")

                            except Exception as e:
                                self.logger.debug(
                                    f"{player.device.name}: Frame decode error:{str(e)}\n{json.dumps(playerFrame, indent=4, sort_keys=True)}")

                        else:
                            self.logger.debug(f"{player.device.name}: Unknown playerFrame:\n{json.dumps(playerFrame, indent=4, sort_keys=True)}")

                self.sleep(0.1)

        except self.StopThread:
            for playerID, player in self.players.items():
                player.stop()

    ########################################
    # Plugin Preference Methods
    ########################################

    def validatePrefsConfigUi(self, valuesDict):
        errorDict = indigo.Dict()

        self.logLevel = int(self.pluginPrefs.get("logLevel", logging.INFO))
        self.indigo_log_handler.setLevel(self.logLevel)

        if len(errorDict) > 0:
            return False, valuesDict, errorDict
        return True, valuesDict

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            self.logLevel = int(self.pluginPrefs.get("logLevel", logging.INFO))
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(f"RFPlayer logLevel = {self.logLevel}")

    ########################################
    # Device Management Methods
    ########################################

    def didDeviceCommPropertyChange(self, origDev, newDev):  # noqa
        if newDev.deviceTypeId == "RFPlayer":
            if origDev.pluginProps.get('serialPort', None) != newDev.pluginProps.get('serialPort', None):
                return True
        return False

    def deviceStartComm(self, device):

        self.logger.debug(f"{device.name}: Starting Device")

        instanceVers = int(device.pluginProps.get('devVersCount', 0))
        if instanceVers == kCurDevVersCount:
            self.logger.threaddebug(f"{device.name}: Device is current version: {instanceVers:d}")
        elif instanceVers < kCurDevVersCount:
            newProps = device.pluginProps
            newProps["devVersCount"] = kCurDevVersCount
            device.replacePluginPropsOnServer(newProps)
            self.logger.debug(f"{device.name}: Updated device version: {instanceVers:d} -> {kCurDevVersCount:d}")
        else:
            self.logger.warning(f"{device.name}: Invalid device version: {instanceVers:d}")

        self.logger.threaddebug(f"{device.name}: Starting Device: {device}")

        if device.deviceTypeId == "RFPlayer":
            serialPort = device.pluginProps.get('serialPort', "")
            baudRate = int(device.pluginProps.get('baudRate', 0))
            player = RFPlayer(self, device)
            if player.start(serialPort, baudRate):
                self.players[device.id] = player
                device.updateStateOnServer(key='playerStatus', value='Starting')
                device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            else:
                device.updateStateOnServer(key='playerStatus', value='Error')
                device.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

        elif device.deviceTypeId == "discoveredDevice":
            address = device.pluginProps.get('address', "")
            protocol = self.knownDevices[address]['protocol']
            self.sensorDevices[address] = (self.protocolClasses[protocol])(device, self.knownDevices)

        elif device.deviceTypeId == "parrotDevice":
            address = device.pluginProps.get('address', "")
            self.sensorDevices[address] = Parrot(device, self.knownDevices)

        elif device.deviceTypeId == "x10Device":
            address = device.pluginProps.get('address', "")
            self.sensorDevices[address] = X10(device, self.knownDevices)

        else:
            self.logger.warning(f"{device.name}: Invalid  device type: {device.deviceTypeId}")

        self.logger.debug(f"{device.name}: deviceStartComm complete, sensorDevices[] =")
        for key, sensor in self.sensorDevices.items():
            self.logger.debug(f"\tkey = {key}, sensor.name = {sensor.device.name}, sensor.id = {sensor.device.id:d}")

    def deviceStopComm(self, device):
        self.logger.debug(f"{device.name}: Stopping Device")
        if device.deviceTypeId == "RFPlayer":
            device.updateStateOnServer(key='playerStatus', value='Stopping')
            device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            player = self.players[device.id]
            player.stop()
            del self.players[device.id]
        else:
            address = device.pluginProps.get('address', "")
            try:
                del self.sensorDevices[address]
            except (Exception,):
                pass

    def deviceDeleted(self, device):
        indigo.PluginBase.deviceDeleted(self, device)

        if device.address:
            try:
                devices = self.knownDevices[device.address]['devices']
                devices.remove(device.id)
                self.knownDevices.setitem_in_item(device.address, 'devices', devices)
                self.knownDevices.setitem_in_item(device.address, 'status', "Available")
                self.logger.debug(f"deviceDeleted: {device.name} ({device.id})")
            except Exception as e:
                self.logger.error(f"deviceDeleted error, {device.name}: {str(e)}")

    ########################################

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):  # noqa
        if typeId == "x10Device":
            valuesDict['address'] = f"X10-{valuesDict['houseCode']}{valuesDict['unitCode']}"
        elif typeId == "parrotDevice":
            valuesDict['address'] = f"PARROT-{valuesDict['houseCode']}{valuesDict['unitCode']}"
        return True, valuesDict

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        return

    # return a list of all "Available" devices (not associated with an Indigo device)

    def availableDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        retList = []
        for address, data in sorted(self.knownDevices.items()):
            if data['status'] == 'Available':
                retList.append((address, f"{address}: {data['description']}"))

        retList.sort(key=lambda tup: tup[1])
        return retList

    # return a list of all "Active" devices of a specific type

    def activeDeviceList(self, filter="", valuesDict=None, typeId="discoveredDevice", targetId=0):
        retList = []
        for address, data in sorted(self.knownDevices.items()):
            if data['status'] == 'Active' and (filter in address):
                retList.append((address, f"{address}: {data['description']}"))

        retList.sort(key=lambda tup: tup[1])
        return retList

    ########################################

    def triggerStartProcessing(self, trigger):
        self.logger.debug(f"Adding Trigger {trigger.name} ({trigger.id:d})")
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.logger.debug(f"Removing Trigger {trigger.name} ({trigger.id:d})")
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

    def triggerCheck(self, device):
        self.logger.threaddebug(f"Checking Triggers for Device {device.name} ({device.id:d})")

        for triggerId, trigger in sorted(self.triggers.items()):
            self.logger.threaddebug(f"\tChecking Trigger {trigger.name} ({trigger.id:d}), {trigger.pluginTypeId}")

            if trigger.pluginProps["sensorID"] != str(device.id):
                self.logger.threaddebug(f"\t\tSkipping Trigger {trigger.name} ({trigger.id}), wrong device: {device.id}")
            else:
                if trigger.pluginTypeId == "sensorFault":
                    if device.states["faultCode"]:  # trigger if faultCode is not None
                        self.logger.debug(f"Executing Trigger {trigger.name} ({trigger.id})")
                        indigo.trigger.execute(trigger)
                    else:
                        self.logger.debug(f"\tNo Match for Trigger {trigger.name} ({trigger.id:d})")
                else:
                    self.logger.threaddebug(f"\tUnknown Trigger Type {trigger.name} ({trigger.id:d}), {trigger.pluginTypeId}")

    ########################################
    # Control Action callbacks
    ########################################

    def actionControlUniversal(self, action, dev):
        if action.deviceAction == indigo.kUniversalAction.RequestStatus:
            sensor = self.sensorDevices[dev.address]
            player = self.players[sensor.player.id]
            sensor.requestStatus(player)

    def actionControlSensor(self, action, dev):
        sensor = self.sensorDevices[dev.address]
        player = self.players[sensor.player.id]

        self.logger.debug(f"actionControlSensor: sensor = {sensor}, player = {player}, action = {action}")

        if action.sensorAction == indigo.kDeviceAction.TurnOn:
            sendSuccess = sensor.turnOn(player)
            if sendSuccess:
                dev.updateStateOnServer("onOffState", True)
            else:
                self.logger.error(f"send '{dev.name}' 'On' failed")

        elif action.sensorAction == indigo.kDeviceAction.TurnOff:
            sendSuccess = sensor.turnOff(player)
            if sendSuccess:
                dev.updateStateOnServer("onOffState", False)
            else:
                self.logger.error(f"send '{dev.name}' 'Off' failed")

        else:
            self.logger.warning(f"Unimplemented command in actionControlSensor: '{dev.name}' -> {action.sensorAction}")

    def actionControlDevice(self, action, dev):
        sensor = self.sensorDevices[dev.address]
        player = self.players[sensor.player.id]

        self.logger.debug(f"actionControlDevice: sensor = {sensor}, player = {player}, action = {action}")

        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            sendSuccess = sensor.turnOn(player)
            if sendSuccess:
                dev.updateStateOnServer("onOffState", True)
            else:
                self.logger.error(f"send '{dev.name}' 'On' failed")

        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            sendSuccess = sensor.turnOff(player)
            if sendSuccess:
                dev.updateStateOnServer("onOffState", False)
            else:
                self.logger.error(f"send '{dev.name}' 'Off' failed")

        else:
            self.logger.warning(f"Unimplemented command in actionControlDevice: '{dev.name}' -> {action.deviceAction}")

    ########################################
    # Plugin Actions object callbacks
    ########################################

    def validateActionConfigUi(self, valuesDict, typeId, devId):    # noqa
        errorsDict = indigo.Dict()

        if len(errorsDict) > 0:
            return False, valuesDict, errorsDict
        return True, valuesDict

    def sendCommandAction(self, pluginAction, playerDevice, callerWaitingForResult):

        player = self.players[playerDevice.id]
        command = indigo.activePlugin.substitute(pluginAction.props["textString"])

        try:
            self.logger.debug(f"sendCommandAction command '{command}' to {playerDevice.name}")
            player.sendRawCommand(command)
        except Exception as e:
            self.logger.exception(f"sendCommandAction error: {e}")

    def sendRTSMyCommand(self, pluginAction, callerWaitingForResult):

        sensorDevice = pluginAction.props["device"]
        sensor = self.sensorDevices[sensorDevice]
        player = self.players[sensor.player.id]
        try:
            self.logger.debug(f"sendRTSMyCommand to {sensorDevice} via {player.device.name}")
            sensor.sendMyCommand(player)
        except Exception as e:
            self.logger.exception(f"sendRTSMyCommand error: {e}")

    def sendX10CommandAction(self, pluginAction, playerDevice, callerWaitingForResult):

        player = self.players[playerDevice.id]
        command = pluginAction.props["command"]
        houseCode = pluginAction.props["houseCode"]
        unitCode = pluginAction.props["unitCode"]

        if command == "DIM":
            brightness = pluginAction.props["brightness"]
            cmdString = f"DIM {houseCode}{unitCode} X10 %{brightness}"
        else:
            cmdString = f"{command} {houseCode}{unitCode} X10"

        try:
            self.logger.debug(f"sendX10CommandAction command '{cmdString}' to {playerDevice.name}")
            player.sendRawCommand(cmdString)
        except Exception as e:
            self.logger.exception(f"sendX10CommandAction error: {e}")

    def setFrequencyAction(self, pluginAction, playerDevice, callerWaitingForResult):

        player = self.players[playerDevice.id]
        band = pluginAction.props["freqBand"]
        lowBand = pluginAction.props["lowBand"]
        highBand = pluginAction.props["highBand"]

        if band == "H":
            command = "FREQ H " + highBand
        elif band == "L":
            command = "FREQ L " + lowBand
        else:
            self.logger.warning(f"setFrequencyAction: Unknown band '{band}'")
            return

        try:
            self.logger.debug(f"setFrequencyAction for {playerDevice.name}, band = {band}, lowBand = {lowBand}, highBand = {highBand} ")
            player.sendRawCommand(command)
            player.sendRawCommand("STATUS RADIO JSON")
        except Exception as e:
            self.logger.exception(f"setFrequencyAction error: {str(e)}")

    ########################################
    # Menu Methods
    ########################################

    # doesn't do anything, just needed to force other menus to dynamically refresh
    def menuChanged(self, valuesDict, typeId, devId):  # noqa
        return valuesDict

    def dumpKnownDevices(self):
        self.logger.info(f"Known device list:\n{self.knownDevices}")

    def purgeKnownDevices(self):
        self.logger.info("Purging Known device list...")
        for address, data in self.knownDevices.items():
            if data['status'] == 'Available':
                self.logger.info(f"\t{address}")
                del self.knownDevices[address]

    def sendCommandMenu(self, valuesDict, typeId):
        try:
            deviceId = int(valuesDict["targetDevice"])
        except (Exception,):
            self.logger.error("Bad Device specified for Send Command operation")
            return False

        try:
            textString = valuesDict["textString"]
        except (Exception,):
            self.logger.error("Bad text string specified for Send Command operation")
            return False

        player = self.players[deviceId]
        command = indigo.activePlugin.substitute(textString)

        try:
            self.logger.debug(f"sendCommandMenu command '{command}' to {indigo.devices[deviceId].name}")
            player.sendRawCommand(command)
        except Exception as e:
            self.logger.exception(f"sendCommandMenu error: {e}")

        return True

    @staticmethod
    def pickSensor(filter=None, valuesDict=None, typeId=0, targetId=0):
        retList = []
        for device in indigo.devices.iter("self"):
            if device.deviceTypeId != "RFPlayer":
                retList.append((device.id, device.name))
        retList.sort(key=lambda tup: tup[1])
        return retList

    @staticmethod
    def pickPlayer(filter=None, valuesDict=None, typeId=0, targetId=0):
        retList = []
        for device in indigo.devices.iter("self"):
            if device.deviceTypeId == "RFPlayer":
                retList.append((device.id, device.name))
        retList.sort(key=lambda tup: tup[1])
        return retList

    @staticmethod
    def pickPlayerDevice(filter=None, valuesDict=None, typeId=0, targetId=0):
        retList = []
        for device in indigo.devices.iter("self"):
            if device.deviceTypeId == "RFPlayer":
                retList.append((device.id, device.name))
        retList.sort(key=lambda tup: tup[1])
        return retList

    def getRFBands(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        rfPlayer = indigo.devices[targetId]
        playerType = rfPlayer.pluginProps[u'playerModel']
        self.logger.debug(f"getRFBands for {rfPlayer.name} ({playerType})")

        if playerType == "US":
            return [("H", "310/315MHz Band"), ("L", "433Mhz Band")]
        elif playerType == "EU":
            return [("H", "868MHz Band"), ("L", "433Mhz Band")]

        self.logger.error(f"Unknown playerType = {playerType} in getRFBands")
        return None

    def getHighBands(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        rfPlayer = indigo.devices[targetId]
        playerType = rfPlayer.pluginProps['playerModel']
        self.logger.debug(f"getHighBands for {rfPlayer.name} ({playerType})")

        if playerType == "US":
            return [("0", "Off"), ("310000", "310MHz - X10 RF"), ("315000", "315MHz - Visonic")]
        elif playerType == "EU":
            return [("0", "Off"), ("868350", "868.350MHz"), ("868950", "868.950MHz")]

        self.logger.error(f"Unknown playerType = {playerType} in getHighBands")
        return None

    def getLowBands(self, filter=None, valuesDict=None, typeId=0, targetId=0):
        rfPlayer = indigo.devices[targetId]
        playerType = rfPlayer.pluginProps[u'playerModel']
        self.logger.debug(f"getLowBands for {rfPlayer.name} ({playerType})")

        if playerType == "US":
            return [("0", "Off"), ("433420", "433.420Mhz - Somfy RTS"), ("433920", "433.920Mhz - Most 433MHz devices")]
        elif playerType == "EU":
            return [("0", "Off"), ("433420", "433.420Mhz"), ("433920", "433.920Mhz")]

        self.logger.error(f"Unknown playerType = {playerType} in getLowBands")
        return None
