#! /usr/bin/env python
# -*- coding: utf-8 -*-

class KD101(object):

    @classmethod
    def getAddress(cls, frameData):
        return "DOMIA-" + frameData['infos']['id']

    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.KD101")
        self.device = device
        self.logger.debug(u"%s: Starting KD101 device" % device.name)

    def handler(self, player, frameData):

        devAddress = "KD101-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: KD101 frame received: %s" % (player.device.name, devAddress))

