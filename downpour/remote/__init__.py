from twisted.internet import reactor, protocol
from downpour.core.plugins import Plugin
from downpour.remote.server import ServerProtocol

class RemotePlugin(Plugin):

    config = None

    def setup(self, config):
        if config is not None and config.get('port', 0) is not None:
            self.config = config
            factory = protocol.ServerFactory()
            factory.protocol = protocolFactory(self)
            factory.application = self.application
            reactor.listenTCP(int(config['port']), factory, interface=config['interface'])

def protocolFactory(plugin):
    def buildProtocol():
        p = ServerProtocol()
        p.plugin = plugin
        return p
    return buildProtocol
