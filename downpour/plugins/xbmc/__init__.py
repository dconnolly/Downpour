from downpour.core.plugins import Plugin
from downpour.plugins.xbmc.remote import XBMCRemote
from twisted.internet import reactor

class XBMCPlugin(Plugin):

    def setup(self, config):

        self.xbmc = XBMCRemote(config['server'],
            config['username'], config['password'])

        self.update_pending = False
        self.update_type = None

        self.clean_pending = False
        self.clean_type = None

        if not 'autoupdate' in config or config['autoupdate']:
            self.application.add_event_listener('library_file_added', self.media_added)

        if 'autoclean' in config and config['autoclean']:
            self.application.add_event_listener('library_file_removed', self.media_removed)

    def media_added(self, filename, download=None):

        if download and download.media_type:
            if download.media_type[:5] == 'audio':
                self.update('audio')
            elif download.media_type[:5] == 'video':
                self.update('video')
        else:
            self.update()

    def media_removed(self, filename, download=None):

        if download and download.media_type:
            if download.media_type[:5] == 'audio':
                self.clean('audio')
            elif download.media_type[:5] == 'video':
                self.clean('video')
        else:
            self.clean()

    def call_on_idle(self, handler):
        dfr = self.xbmc.get_active_players()
        dfr.addCallback(handler)

    def update(self, library=None):
        if self.update_pending:
            if self.update_type != library:
                # Multiple update requests, update all libs
                self.update_type = None
        else:
            self.update_pending = True
            self.update_type = library
            self.call_on_idle(self.update_if_idle)

    def update_if_idle(self, response):
        if not response['video'] and not response['picture']:
            self.update_pending = False
            library = self.update_type
            self.update_type = None
            self.xbmc.update(library)
        else:
            reactor.callLater(10.0, self.call_on_idle, self.update_if_idle)

    def clean(self, library=None):
        if self.clean_pending:
            if self.clean_type != library:
                # Multiple clean requests, clean all libs
                self.clean_type = None
        else:
            self.clean_pending = True
            self.clean_type = library
            self.call_on_idle(self.clean_if_idle)

    def clean_if_idle(self, response):
        if not response['video'] and not response['picture']:
            self.clean_pending = False
            library = self.clean_type
            self.clean_type = None
            self.xbmc.clean(library)
        else:
            reactor.callLater(10.0, self.call_on_idle, self.clean_if_idle)
