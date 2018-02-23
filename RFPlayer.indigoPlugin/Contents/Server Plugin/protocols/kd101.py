    def kd101Handler(self, player, frameData):

        devAddress = "KD101-" + frameData['infos']['id']

        self.logger.debug(u"%s: KD101 frame received: %s" % (player.device.name, devAddress))

