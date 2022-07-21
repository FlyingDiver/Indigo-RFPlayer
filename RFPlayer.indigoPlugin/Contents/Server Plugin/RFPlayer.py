#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2017, Joe Keenan, joe@flyingdiver.com

import json
import logging
import serial

from queue import Queue

################################################################################
class RFPlayer(object):

    def __init__(self, plugin, device):
        self.logger = logging.getLogger("Plugin.RFPlayer")
        self.plugin = plugin
        self.device = device
        self.port = None
        self.sequence = 0
        self.queue = Queue()
        self.connected = False

    def __del__(self):
        pass

    def start(self, serialPort, baudRate):

        self.logger.debug(f"RFPlayer start called, port = {serialPort}, baud = {baudRate:d}")

        if len(serialPort) == 0:
            self.logger.debug("RFPlayer start: no serial port specified")
            return False
        
        if baudRate == 0:
            self.logger.debug("RFPlayer start: invalid baud rate")
            return False
        
        self.sequence = 0
        
        self.port = self.plugin.openSerial("RFPlayer", serialPort, baudRate, timeout=0, writeTimeout=1, rtscts=True)
        if self.port is None:
            return False
        else:
            self.logger.info(f"Opened serial port {serialPort} at {baudRate:d} baud")
            self.connected = True
                 
        self.sendRawCommand("HELLO")
        self.sendRawCommand("FORMAT JSON")
        self.sendRawCommand("STATUS SYSTEM JSON")
        self.sendRawCommand("STATUS RADIO JSON")
        return True

    def stop(self):
        self.logger.debug("RFPlayer stop called")
        if self.connected:
            self.port.close()
        self.port = None  
       
    def poll(self):
    
        reply = None
        if not self.connected:
            return reply
            
        # first look for incoming frames
        
        data = ""
        try:
            if self.port.in_waiting > 0:
                while not data.endswith('\r'):
                    data += self.port.read().decode('ascii')
                reply = self.handle_data(data.rstrip())
        except Exception as e:
            self.logger.error(f"RFPlayer Serial Read error: {e}")
            self.connected = False
        
        # now send any queued up messages
        
        if not self.queue.empty():
            command = self.queue.get(False)
            self.logger.threaddebug(f"sending: {command}")
            try:
                self.port.write(command.encode('ascii'))
            except Exception as e:
                self.logger.exception(f"Serial Write error: {e}")
                self.connected = False
            
        return reply
   
    def handle_data(self, data):
        
        if data[0:3] != "ZIA":
            self.logger.debug(f"Invalid frame prefix: '{data[0:3]}'")
            return

        if data[0:12] == "ZIA--Welcome":    # Welcome reply, always text string
            self.logger.info(data[5:])
            return
        
        if data[0:5] == "ZIA55":            # Trace log event
            self.logger.debug("!! Trace" + data[5:])
            return
        
        try:                                # everything else should be JSON
            reply = json.loads(data[5:])
        except Exception as e:
            self.logger.debug(f"json decode failure:{e}\n{data}")
            return None
        else:
            return reply

    def sendCommand(self, commandString):
    
        self.logger.threaddebug(f"sendCommand: {commandString}")
        self.sequence += 1 
        command = f"ZIA++{self.sequence:04d} {commandString} JSON\r"
        self.queue.put(command)

    def sendRawCommand(self, commandString):
    
        self.logger.threaddebug(f"sendRawCommand: {commandString}")
        command = f"ZIA++{commandString}\r"
        self.queue.put(command)
        
        
        