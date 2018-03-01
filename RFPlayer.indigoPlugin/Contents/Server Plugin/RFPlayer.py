#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2017, Joe Keenan, joe@flyingdiver.com

import json
import logging
import serial

from Queue import Queue

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

        self.logger.debug(u"RFPlayer start called, port = %s, baud = %d" % (serialPort, baudRate))

        if len(serialPort) == 0:
            self.logger.debug(u"RFPlayer start: no serial port specified")
            return False
        
        if baudRate == 0:
            self.logger.debug(u"RFPlayer start: invalid baud rate")
            return False
        
        self.sequence = 0
        
        self.port = self.plugin.openSerial("RFPlayer", serialPort, baudRate, timeout=0, writeTimeout=1, rtscts=True)
        if self.port is None:
            self.logger.error(u"serial port could not be opened", isError=True)
            return False
        else:
            self.logger.info(u"Opened serial port %s at %d baud" % (serialPort, baudRate)) 
            self.connected = True
                 
        self.sendRawCommand("HELLO")
        self.sendRawCommand("FORMAT JSON")
        self.sendRawCommand("STATUS SYSTEM JSON")
        self.sendRawCommand("STATUS RADIO JSON")
        
        return True
            

    def stop(self):
        self.logger.debug(u"RFPlayer stop called")
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
        except Exception, e:
            self.logger.error(u"Serial Read error: %s" % str(e))
            self.connected = False
        
        # now send any queued up messages
        
        if not self.queue.empty():
            command = self.queue.get(False)
            self.logger.threaddebug(u"sending: " + command)
            try:
                self.port.write(command)
            except Exception, e:
                self.logger.exception(u"Serial Write error: %s" % str(e))
            
        return reply
   
    def handle_data(self, data):
        
        if data[0:3] != "ZIA":
            self.logger.debug(u"Invalid frame prefix: '%s'" % data[0:3])
            return

        if data[0:12] == "ZIA--Welcome":    # Welcome reply, always text string
            self.logger.info(data[5:])
            return
        
        if data[0:5] == "ZIA55":            # Trace log event
            self.logger.debug("!! Trace" + data[5:])
            return
        
        try:                                # everything else should be JSON
            reply = json.loads(data[5:])
            return reply
        except:
            self.logger.debug(u"json decode failure:\n" + str(data))        
        
        return None
        
    def sendCommand(self, commandString):
    
        self.logger.threaddebug(u"sendCommand: " + commandString)
        self.sequence += 1 
        command = "ZIA++%04d %s JSON\r" % (self.sequence, commandString)
        self.queue.put(command)
        
    
    def sendRawCommand(self, commandString):
    
        self.logger.threaddebug(u"sendRawCommand: " + commandString)
        command = "ZIA++%s\r" % (commandString)
        self.queue.put(command)
        
        
        