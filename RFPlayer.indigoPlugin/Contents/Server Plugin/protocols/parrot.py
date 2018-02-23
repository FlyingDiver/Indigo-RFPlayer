    def parrotHandler(self, player, frameData):

        devAddress = "PARROT-" + frameData['infos']['idMeaning']

        self.logger.debug(u"%s: Parrot frame received: %s" % (player.device.name, devAddress))
        
