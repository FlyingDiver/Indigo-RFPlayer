#! /usr/bin/env python
# -*- coding: utf-8 -*-

class Owl(object):

    @classmethod
    def getAddress(cls, frameData):
        return "DOMIA-" + frameData['infos']['id']

    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.Owl")
        self.device = device
        self.logger.debug(u"%s: Starting Owl device" % device.name)

    def handler(self, player, frameData):

        devAddress = "OWL-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: Owl frame received: %s" % (player.device.name, devAddress))

