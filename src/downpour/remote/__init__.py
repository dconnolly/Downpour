from twisted.internet import reactor, protocol
from downpour.core.plugins import Plugin
from downpour.remote.server import ServerProtocol

class RemotePlugin(Plugin):

    def setup(self, config):
        if config is not None and config.get('port', 0) is not None:
            factory = protocol.ServerFactory()
            factory.protocol = protocolFactory(self)
            factory.application = self.application
            reactor.listenTCP(int(config['port']), factory, interface=config['interface'])

def protocolFactory(plugin):
    p = ServerProtocol()
    p.plugin = plugin
