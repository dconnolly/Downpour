from twisted.internet import protocol, reactor, defer
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.python import failure
import logging
import os

class RemoteClientProtocol(protocol.Protocol):
    
    dfr = None
    response = None
    payload = None

    def auth(self, password, data=None):
        return self.sendCommand('PASS %s' % password)

    def status(self, password, data=None):
        return self.sendCommand('STATUS')

    def torrent(self, input, data=None):

        command = None
        payload = None

        if input == 'addfile':
            # Local file
            if os.access(data, os.F_OK) and os.access(data, os.R_OK):
                f = open(data)
                command = 'ADDRAW'
                payload = f.read()
                f.close()
            else:
                raise RemoteClientError
        elif input == 'add':
            command = 'ADDURL %s' % data
        elif input == 'list':
            command = 'LIST'
        elif input == 'DETAIL':
            command = 'DETAIL %s' % data

        return self.sendCommand('TORRENT %s' % command, payload)
    
    def feed(self, input, data=None):
        pass

    # Prevent command overlap
    def sendCommand(self, command, payload=None):

        if self.dfr:
            raise ProtocolError('Attempt to send new command before previous command completed')

        self.response = None
        self.dfr = defer.Deferred()

        self.transport.write('%s\n' % command)

        if payload:
            pdfr = defer.Deferred()
            def sendBlob(p):
                self.dfr = pdfr
                if p.response != 'READY':
                    self.dfr.errback(ProtocolError('Bad response from server.'))
                    return
                self.response = None
                self.transport.write('BLOB LENGTH %d\n' % len(payload))
                self.transport.write(payload)
            self.dfr.addCallback(sendBlob)
            return pdfr

        return self.dfr

    # General message-handling
    def connectionMade(self):
        logging.debug('p: Connected')
        
    def dataReceived(self, data):
        response_complete = False
        success = False

        logging.debug('p: Data received: ', data)

        if self.response:
            self.response += data
        else:
            self.response = data

        if self.response == 'OK\n' or self.response.endswith('\nOK\n'):
            response_complete = True
            self.response = self.response[0:len(self.response)-3]
            success = True
        elif self.response == 'READY\n':
            response_complete = True
            self.response = self.response.rstrip()
            success = True
        elif self.response == 'ERR\n' or self.response.endswith('\nERR\n'):
            response_complete = True
            self.response = self.response[0:len(self.response)-4]
            success = False

        if response_complete and self.dfr:
            # Rest Deferrred ref in case callbacks need to execute more commands
            dfr = self.dfr
            self.dfr = None
            if success:
                dfr.callback(self)
            else:
                dfr.errback(ProtocolError('Request failed: %s' % self.response))
        
    def connectionLost(self, reason):
        logging.debug('p: Disconnected: ', reason)

class RemoteClientFactory(ReconnectingClientFactory):
    def startedConnecting(self, connector):
        logging.debug('f: Started to connect.')

    def buildProtocol(self, addr):
        logging.debug('f: Connected')
        self.resetDelay()
        return RemoteClientProtocol()

    def clientConnectionLost(self, connector, reason):
        logging.debug('f: Disconnected: ', reason)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        logging.debug('f: Connection failed: ', reason)
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

class ProtocolError(RuntimeError):
    pass
