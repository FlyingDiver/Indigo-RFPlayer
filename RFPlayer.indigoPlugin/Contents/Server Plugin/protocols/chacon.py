    def chaconHandler(self, player, frameData):

        devAddress = "CHACON-" + frameData['infos']['id']

        self.logger.debug(u"%s: Chacon frame received: %s" % (player.device.name, devAddress))

