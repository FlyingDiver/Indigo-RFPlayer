    def owlHandler(self, player, frameData):

        devAddress = "OWL-" + frameData['infos']['id']

        self.logger.debug(u"%s: Owl frame received: %s" % (player.device.name, devAddress))

