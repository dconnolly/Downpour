from downpour.remote import commands
from downpour.core import models
from twisted.protocols import amp
from twisted.internet.protocol import Factory
import logging

class ServerProtocol(amp.AMP):

    authorized = False

    def check_auth(self):
        if not self.authorized:
            raise Exception('Not authorized, login required')

    def auth(self, password): 
        self.authorized = (password == self.config['password'])
        return {'result': self.authorized}

    commands.Auth.responder(auth)
    
    def status(self):
        self.check_auth()
        status = self.factory.application.manager.get_status()
        return {'result': status}

    commands.Status.responder(status)

    def download_add(self, url):
        self.check_auth()
        d = models.Download()
        d.url = url
        return {'result': self.factory.application.manager.add_download(d)}

    commands.DownloadAdd.responder(download_add)

    def torrent_add_file(self, data):
        self.check_auth()
        return {'result': self.factory.application.manager.add_torrent_raw(data)}

    commands.TorrentAddFile.responder(torrent_add_file)

    def download_list(self):
        self.check_auth()
        m = self.factory.application.manager
        downloads = m.get_downloads()

        return {'result': [{
                'id': d.id,
                'url': d.url,
                'filename': d.filename,
                'feed': d.feed_id,
                'media_type': d.media_type,
                'mime_type': d.mime_type,
                'description': d.description,
                'download_directory': d.download_directory,
                'rename_pattern': d.rename_pattern,
                'active': d.active,
                'status': d.status,
                'status_message': d.status_message,
                'progress': d.progress,
                'size': d.size,
                'downloaded': d.downloaded,
                'added': d.added,
                'started': d.started,
                'completed': d.completed,
                # Non-persistent fields from libtorrent
                'peers': d.peers,
                'seeds': d.seeds,
                'state': d.state,
                'paused': d.paused,
                'uploadrate': d.uploadrate,
                'uploaded': d.uploaded,
                'downloadrate': d.downloadrate,
                'elapsed': d.elapsed,
                'timeleft': d.timeleft
            } for d in downloads]
        }

    commands.DownloadList.responder(download_list)

    def download_info(self, id):
        self.check_auth()
        m = self.factory.application.manager
        d = m.get_download(id)
        dc = m.get_download_client(id)
        return {'result': {
                'id': d.id,
                'url': d.url,
                'filename': d.filename,
                'feed': d.feed_id,
                'media_type': d.media_type,
                'mime_type': d.mime_type,
                'description': d.description,
                'download_directory': d.download_directory,
                'rename_pattern': d.rename_pattern,
                'active': d.active,
                'status': d.status,
                'status_message': d.status_message,
                'progress': d.progress,
                'size': d.size,
                'downloaded': d.downloaded,
                'added': d.added,
                'started': d.started,
                'completed': d.completed,
                # Non-persistent fields from libtorrent
                'files': [{'index': f.index,
                            'path': f.path,
                            'type': f.type,
                            'size': f.size} for f in dc.get_files() if dc],
                'peers': d.peers,
                'seeds': d.seeds,
                'state': d.state,
                'paused': d.paused,
                'uploadrate': d.upload_rate,
                'uploaded': d.uploaded,
                'downloadrate': d.downloadrate,
                'elapsed': d.elapsed,
                'timeleft': d.timeleft
            }}

    commands.DownloadInfo.responder(download_info)

    def download_control(self, id, action):
        self.check_auth()
        m = self.factory.application.manager
        actions = {
            'stop': m.pause_download,
            'start': m.resume_download,
            'delete': m.remove_download,
        }
        if actions.has_key(action):
            return {'result': actions[action](id)}
        raise Exception('Invalid command')

    commands.DownloadControl.responder(download_control)

    def download_remove(self, id):
        self.check_auth()
        return {'result': self.factory.application.manager.remove_download(id)}

    commands.DownloadRemove.responder(download_remove)

    def feed_add(self, url=None, name=None, media_type=None):
        self.check_auth()
        f = models.Feed()
        f.url = url
        f.name = name
        f.media_type = media_type
        return {'result': self.factory.application.manager.add_feed(f)}

    commands.FeedAdd.responder(feed_add)

    def feed_list(self):
        self.check_auth()
        m = self.factory.application.manager
        feeds = m.get_feeds()
        return {'result': [
                {'id': f.id,
                'name': f.name,
                'url': f.url,
                'media_type': f.media_type,
                'series': f.series_id,
                'active': f.active,
                'last_update': f.last_update,
                'last_error': f.last_error,
                'update_frequency': f.update_frequency,
                'download_directory': f.download_directory,
                'rename_pattern': f.rename_pattern,
                'match_pattern': f.match_pattern,
                } for f in feeds ]}

    commands.FeedList.responder(feed_list)

    def feed_info(self, id):
        self.check_auth()
        m = self.factory.application.manager
        f = m.get_feed(id)
        downloads = self.factory.application.get_store().find(models.Download, models.Download.feed_id==f.id)
        return {'result': {
                    'id': f.id,
                    'name': f.name,
                    'url': f.url,
                    'media_type': f.media_type,
                    'series': f.series_id,
                    'active': f.active,
                    'last_update': f.last_update,
                    'last_error': f.last_error,
                    'update_frequency': f.update_frequency,
                    'download_directory': f.download_directory,
                    'rename_pattern': f.rename_pattern,
                    'match_pattern': f.match_pattern,
                    'active_downloads': [{'id': d.id, 'name': d.name} for d in downloads]
            }}

    commands.FeedInfo.responder(feed_info)

    def feed_update(self, id, values):
        self.check_auth()
        m = self.factory.application.manager
        f = m.get_feed(id)
        # TODO: update object from dict
        return {'result': True}

    commands.FeedUpdate.responder(feed_update)

    def feed_remove(self, id):
        self.check_auth()
        return {'result': self.factory.application.manager.remove_feed(id)}

    commands.FeedRemove.responder(feed_remove)
