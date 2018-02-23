    def x2dHandler(self, player, frameData):

        devAddress = "X2D-" + frameData['infos']['id']

        self.logger.debug(u"%s: X2D frame received: %s" % (player.device.name, devAddress))

