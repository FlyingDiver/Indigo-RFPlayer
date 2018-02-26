class X2D(object):

    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.X2D")
        self.device = device
        self.logger.debug(u"%s: Starting X2D device" % device.name)

    def handler(self, player, frameData):

        devAddress = "X2D-" + frameData['infos']['id']

        self.logger.threaddebug(u"%s: X2D frame received: %s" % (player.device.name, devAddress))

