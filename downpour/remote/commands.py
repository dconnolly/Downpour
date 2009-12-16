from twisted.protocols import amp
from downpour.remote import types

class Auth(amp.Command):
    arguments = [('password', amp.Unicode())]
    response = [('result', amp.Boolean())]
    errors = {Exception: 'EXCEPTION'}

class Status(amp.Command):
    response = [('result', types.Dict([
            ('host', amp.Unicode()),
            ('version', amp.Unicode()),
            ('downloads', amp.Integer()),
            ('active_downloads', amp.Integer()),
            ('downloadrate', amp.Float()),
            ('uploadrate', amp.Float()),
            ('connections', amp.Integer()),
            ('paused', amp.Boolean()),
        ]))]
    errors = {Exception: 'EXCEPTION'}

class DownloadAdd(amp.Command):
    arguments = [('url', amp.Unicode())]
    response = [('result', amp.Integer())]
    errors = {Exception: 'EXCEPTION'}

class TorrentAddFile(amp.Command):
    arguments = [('data', amp.String())]
    response = [('result', amp.Integer())]
    errors = {Exception: 'EXCEPTION'}

class DownloadList(amp.Command):
    response = [('result', amp.AmpList([
            ('id', amp.Integer()),
            ('url', amp.Unicode(True)),
            ('filename', amp.Unicode(True)),
            ('feed', amp.Integer(True)),
            ('media_type', amp.Unicode()),
            ('mime_type', amp.Unicode(True)),
            ('description', amp.Unicode(True)),
            ('download_directory', amp.Unicode(True)),
            ('rename_pattern', amp.Unicode(True)),
            ('status', amp.Integer(True)),
            ('status_message', amp.Unicode(True)),
            ('progress', amp.Float()),
            ('size', amp.Integer(True)),
            ('downloaded', amp.Integer(True)),
            ('added', amp.Integer()),
            ('started', amp.Integer(True)),
            ('completed', amp.Integer(True)),
            ('deleted', amp.Boolean(True)),
            # Non-persistent fields
            ('peers', amp.Integer(True)),
            ('seeds', amp.Integer(True)),
            ('state', amp.Unicode(True)),
            ('paused', amp.Boolean(True)),
            ('uploadrate', amp.Float(True)),
            ('uploaded', amp.Integer(True)),
            ('downloadrate', amp.Float(True)),
            ('elapsed', amp.Integer(True)),
            ('timeleft', amp.Integer(True))
        ]))]
    errors = {Exception: 'EXCEPTION'}

class DownloadInfo(amp.Command):
    arguments = [('id', amp.Integer())]
    response = [('result', types.Dict([
            ('id', amp.Integer()),
            ('url', amp.Unicode(True)),
            ('filename', amp.Unicode(True)),
            ('feed', amp.Integer(True)),
            ('media_type', amp.Unicode()),
            ('mime_type', amp.Unicode()),
            ('description', amp.Unicode(True)),
            ('download_directory', amp.Unicode(True)),
            ('rename_pattern', amp.Unicode(True)),
            ('status', amp.Integer(True)),
            ('status_message', amp.Unicode(True)),
            ('progress', amp.Float()),
            ('size', amp.Integer(True)),
            ('downloaded', amp.Integer(True)),
            ('added', amp.Integer()),
            ('started', amp.Integer(True)),
            ('completed', amp.Integer(True)),
            ('deleted', amp.Boolean(True)),
            # Non-persistent fields from libtorrent
            ('files', amp.AmpList([
                    ('index', amp.Integer()),
                    ('path', amp.Unicode()),
                    ('type', amp.Unicode()),
                    ('size', amp.Integer())
                ])),
            ('peers', amp.Integer(True)),
            ('seeds', amp.Integer(True)),
            ('state', amp.Unicode(True)),
            ('paused', amp.Boolean(True)),
            ('uploadrate', amp.Float(True)),
            ('uploaded', amp.Integer(True)),
            ('downloadrate', amp.Float(True)),
            ('elapsed', amp.Integer(True)),
            ('timeleft', amp.Integer(True))
        ]))]
    errors = {Exception: 'EXCEPTION'}

class DownloadControl(amp.Command):
    arguments = [('id', amp.Integer()), ('action', amp.Unicode())]
    response = [('result', amp.Boolean())]
    errors = {Exception: 'EXCEPTION'}

class DownloadRemove(amp.Command):
    arguments = [('id', amp.Integer())]
    response = [('result', amp.Boolean())]
    errors = {Exception: 'EXCEPTION'}

class FeedAdd(amp.Command):
    arguments = [('url', amp.Unicode()),
                ('name', amp.Unicode(True)),
                ('media_type', amp.Unicode(True))]
    response = [('result', amp.Integer())]
    errors = {Exception: 'EXCEPTION'}

class FeedList(amp.Command):
    response = [('result', amp.AmpList([
            ('id', amp.Integer()),
            ('name', amp.Unicode(True)),
            ('url', amp.Unicode()),
            ('media_type', amp.Unicode(True)),
            ('series', amp.Integer(True)),
            ('active', amp.Boolean(True)),
            ('last_update', amp.Integer(True)),
            ('last_error', amp.Unicode(True)),
            ('update_frequency', amp.Integer()),
            ('download_directory', amp.Unicode(True)),
            ('rename_pattern', amp.Unicode(True)),
            ('match_pattern', amp.Unicode(True))
        ]))]
    errors = {Exception: 'EXCEPTION'}

class FeedInfo(amp.Command):
    arguments = [('id', amp.Integer())]
    response = [('result', types.Dict([
            ('id', amp.Integer()),
            ('name', amp.Unicode(True)),
            ('url', amp.Unicode()),
            ('media_type', amp.Unicode(True)),
            ('series', amp.Integer(True)),
            ('active', amp.Boolean(True)),
            ('last_update', amp.Integer(True)),
            ('last_error', amp.Unicode(True)),
            ('update_frequency', amp.Integer()),
            ('download_directory', amp.Unicode(True)),
            ('rename_pattern', amp.Unicode(True)),
            ('match_pattern', amp.Unicode(True)),
            ('active_downloads', amp.AmpList([
                    ('id', amp.Integer()),
                    ('name', amp.Unicode())
                ])),
        ]))]
    errors = {Exception: 'EXCEPTION'}

class FeedUpdate(amp.Command):
    arguments = [('id', amp.Integer()), ('values', types.Dict([
            ('name', amp.Unicode(True)),
            ('url', amp.Unicode(True)),
            ('media_type', amp.Unicode(True)),
            ('series', amp.Integer(True)),
            ('active', amp.Boolean(True)),
            ('update_frequency', amp.Integer(True)),
            ('download_directory', amp.Unicode(True)),
            ('rename_pattern', amp.Unicode(True)),
            ('match_pattern', amp.Unicode(True))
        ]))]
    response = [('result', amp.Boolean())]
    errors = {Exception: 'EXCEPTION'}

class FeedRemove(amp.Command):
    arguments = [('id', amp.Integer())]
    response = [('result', amp.Boolean())]
    errors = {Exception: 'EXCEPTION'}
