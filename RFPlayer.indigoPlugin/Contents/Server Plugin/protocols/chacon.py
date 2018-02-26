#! /usr/bin/env python
# -*- coding: utf-8 -*-

class Chacon(object):

    @classmethod
    def getAddress(cls, frameData):
        return "CHACON-" + frameData['infos']['id']

    
    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.Chacon")
        self.device = device
        self.logger.debug(u"%s: Starting Chacon device" % device.name)

    def handler(self, player, frameData):

        devAddress = "CHACON-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: Chacon frame received: %s" % (player.device.name, devAddress))

