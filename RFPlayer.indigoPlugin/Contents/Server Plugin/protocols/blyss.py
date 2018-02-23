    def blyssHandler(self, player, frameData):

        devAddress = "BLYSS-" + frameData['infos']['id']

        self.logger.debug(u"%s: Sensor Blyss received: %s" % (player.device.name, devAddress))

