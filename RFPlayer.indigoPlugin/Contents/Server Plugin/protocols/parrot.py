class Parrot(object):

    def __init__(self, device):
        self.logger = logging.getLogger("Plugin.Parrot")
        self.device = device
        self.logger.debug(u"%s: Starting Parrot device '%s'" % (device.name,device.address))

        device.name = device.address
        device.replaceOnServer()
        if device.address not in self.knownDevices:
            self.logger.info("New Parrot Device %s" % (device.address))
            self.knownDevices[device.address] = { 
                "status": "Active", 
                "devices" : [device.id],
                "protocol": "1", 
                "protocolMeaning": "Parrot", 
                "infoType": "0", 
                "subType": 'None',
                "description": device.address,
            }
            self.logger.debug(u"added new known device: %s = %s" % (device.address, unicode(self.knownDevices[device.address])))

    def handler(self, player, frameData):

        devAddress = "PARROT-" + frameData['infos']['idMeaning']

        self.logger.threaddebug(u"%s: Parrot frame received: %s" % (player.device.name, devAddress))
        
