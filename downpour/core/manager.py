from downpour.core import VERSION, models, organizer
from downpour.download import Status
from downpour.download.http import HTTPDownloadClient
from downpour.download.torrent import LibtorrentClient
from twisted.web import http
from twisted.internet import threads, defer
from time import time
from urlparse import urlparse
import feedparser, os, mimetypes, logging, tempfile, shutil

class Manager:

    download_clients = []

    client_mimetypes = {
        'application/x-bittorrent': LibtorrentClient
        }
    client_protocols = {
        'http': HTTPDownloadClient,
        'https': HTTPDownloadClient
        }

    def __init__(self, application):
        self.application = application
        self.store = application.get_store()
        self.paused = self.application.is_paused()

    def get_status(self):
        downloads = self.get_downloads()
        queuedsize = sum([d.size for d in downloads if d.size])
        if queuedsize:
            queueddone = sum([d.downloaded for d in downloads])
            progress = round((float(queueddone) / queuedsize) * 100, 2)
        else:
            progress = 0

        s = os.statvfs(self.get_work_directory())
        diskfree = s.f_bfree * s.f_bsize
        diskfreepct = (float(s.f_bfree) / s.f_blocks) * 100

        s = os.statvfs(self.get_user_directory())
        userdiskfree = s.f_bfree * s.f_bsize
        userdiskfreepct = (float(s.f_bfree) / s.f_blocks) * 100

        active_downloads = len([d for d in downloads if d.active])
        download_rate = sum([d.downloadrate for d in downloads])
        upload_rate = sum([d.uploadrate for d in downloads])
        connections = sum([d.connections for d in downloads])
        status = {'host': self.get_option(('downpour', 'interface'), 'localhost'),
                'version': VERSION,
                'downloads': len(downloads),
                'active_downloads': active_downloads,
                'downloadrate': download_rate,
                'uploadrate': upload_rate,
                'progress': progress,
                'diskfree': diskfree,
                'diskfreepct': diskfreepct,
                'userdiskfree': userdiskfree,
                'userdiskfreepct': userdiskfreepct,
                'connections': connections,
                'paused': self.paused
            }
        return status
    
    def add_download(self, d):
        max_queued = int(self.get_setting('max_queued', 0))
        if max_queued and (len(self.get_downloads()) >= max_queued):
            raise Exception('Too many downloads queued (see "max_queued" config var)')

        if d.url:
            if not d.description:
                d.description = d.url
            if not d.filename:
                d.filename = unicode(os.path.basename(http.urlparse(str(d.url))[2]))

        # Rather than guess mimetypes, just let default downloaders grab
        # the file and pass it off to secondary handlers if needed
        #if d.filename and not d.mime_type:
            #d.mime_type = unicode(mimetypes.guess_type(d.filename)[0])

        if not d.feed_id and not d.media_type:
            mt = d.mime_type
            if not mt and d.filename:
                mt = mimetypes.guess_type(d.filename)[0]
            if mt:
                if mt.startswith('video'):
                    d.media_type = u'video/other'
                elif mt.startswith('audio'):
                    d.media_type = u'audio/other'

        d.added = time()
        d.deleted = False
        d.active = False
        d.progress = 0
        d.status = Status.QUEUED
        d.downloaded = 0

        self.store.add(d)
        self.store.commit()
        logging.debug(u'Added new download ' + d.description)

        self.application.auto_queue()

        return d.id

    def get_downloads(self):
        raise NotImplementedError('Manager must be subclassed')

    def get_download(self, id):
        for d in self.get_downloads():
            if d.id == id:
                return d
        raise Exception('Download not found')

    def pause_download(self, id):
        d = self.get_download(id)
        dc = self.get_download_client(id)
        dfr = None
        if dc and dc.is_stoppable():
            logging.debug(u'Pausing download %s (%s)' % (d.id, d.description))
            dfr = defer.maybeDeferred(dc.pause)
            dfr.addCallback(self.update_status, d, Status.STOPPED)
            dfr.addErrback(self.update_status, d, Status.STOPPED)
        else:
            dfr = defer.succeed(True)
        self.store.commit()
        return dfr

    def resume_download(self, id):
        d = self.get_download(id)
        try:
            dc = self.get_download_client(id)
            dfr = None
            if not self.paused and dc and dc.is_startable():
                logging.debug(u'Resuming download %s (%s)' % (d.id, d.description))
                dfr = defer.maybeDeferred(dc.resume)
                if not d.started:
                    d.started = time()
            else:
                dfr = defer.succeed(True)
            self.store.commit()
            return dfr
        except Exception as e:
            d.status = Status.FAILED
            d.status_message = unicode(e)
            logging.debug(u'Download failed: %s' % d.status_message)

    def remove_download(self, id, remove_files=True):
        d = self.get_download(id)
        dfr = self.stop_download(id)
        dfr.addCallback(self.remove_download_success, d, remove_files)
        dfr.addErrback(self.remove_download_success, d, remove_files)
        return dfr

    def remove_download_success(self, result, d, remove_files=True):
        if not d:
            return
        dc = self.get_download_client(d.id)
        if dc:
            dc.remove()
            Manager.download_clients.remove(dc)
        d.deleted = True
        self.store.commit()
        try:
            if remove_files:
                workdir = self.get_work_directory(d)
                if os.path.isdir(workdir):
                    shutil.rmtree(workdir)
        except Exception as e:
            logging.debug(e)

        logging.debug(u'Removed download %s (%s)' % (d.id, d.description))

    def remove_download_failed(self, failure, dc, d):
        d.status_message = unicode(failure.getErrorMessage())
        logging.debug(u'Failed to stop download %s: %s' % (d.id, failure.getErrorMessage()))

    def get_work_directory(self, download=None):
        workdir = os.path.expanduser(
                self.get_option(('downpour', 'work_directory'),
                                tempfile.gettempdir()))
        if download:
            workdir = os.path.join(workdir, 'dldir%s' % download.id)
        return workdir

    def get_download_client(self, id, create=False):
        d = self.get_download(id)
        for dc in Manager.download_clients:
            if dc.download.id == id:
                return dc

        if create:
            clientdir = self.get_work_directory(d)
            client = None
            if d.mime_type and d.mime_type in self.client_mimetypes:
                client = self.client_mimetypes[d.mime_type](d, self, clientdir)
            elif d.url:
                protocol = urlparse(d.url).scheme
                if protocol in Manager.client_protocols:
                    client = Manager.client_protocols[protocol](d, self, clientdir)
            Manager.download_clients.append(client);
            client.addCallback(self.download_complete, client, d)
            client.addErrback(self.download_failed, client, d)
            return client

    def download_complete(self, new_mimetype, dc, d):
        if new_mimetype:
            Manager.download_clients.remove(dc)
            ndc = self.get_download_client(d.id, True)
            if ndc and dc.__class__ != ndc.__class__:
                # New mimetype requires different download handler,
                # we just downloaded a metadata file
                logging.debug(u'Got metadata for %s (%s)' % (d.id, d.description))
                metafile = self.get_work_directory(d) + '/' + d.filename
                if os.access(metafile, os.R_OK):
                    f = open(metafile, 'rb')
                    d.metadata = f.read()
                    f.close()
                d.progress = 0
                self.start_download(d.id)
                return
        d.status = Status.COMPLETED
        d.active = False
        d.completed = time()
        d.status_message = None
        self.store.commit()
        logging.debug(u'Finished downloading %s (%s)' % (d.id, d.description))
        # NOTE: if upload_ratio is > 0, this will not get run until
        # seeding is finished!
        self.process_download(d, dc)

    def process_download(self, d, dc):
        dfr = organizer.process_download(self.application.get_manager(d.user), d, dc)
        dfr.addCallback(self.process_download_complete, d)
        dfr.addErrback(self.process_download_failed, d)

    def process_download_complete(self, result, d):
        d.imported = True
        d.status_message = None
        if d.feed and d.feed.auto_clean:
            remove_download(d.id);
        logging.debug(u'Imported %s (%s)' % (d.id, d.description))
        self.store.commit()

    def process_download_failed(self, failure, d):
        d.status_message = unicode(failure.getErrorMessage())
        logging.debug(u'Imported failed for %s (%s)' % (d.id, d.description))
        logging.debug(str(failure))
        self.store.commit()

    def download_failed(self, failure, dc, d):
        d.status = Status.FAILED
        d.active = False
        d.status_message = unicode(failure.getErrorMessage())
        self.store.commit()
        logging.debug(str(failure))
        logging.debug(u'Download %s failed: %s' % (d.id, failure.getErrorMessage()))

    def start_download(self, id, force=False):
        d = self.get_download(id)
        try:
            dc = self.get_download_client(id, True)
            d.active = True
            d.status_message = None
            dfr = None
            if not self.paused and dc and (dc.is_startable() or force):
                logging.debug(u'Starting download %s (%s)' % (d.id, d.description))
                dfr = defer.maybeDeferred(dc.start)
                dfr.addErrback(self.download_failed, dc, d)
                if not d.started:
                    d.started = time()
            else:
                dfr = defer.succeed(False)
            self.store.commit()
            return dfr
        except Exception as e:
            d.status = Status.FAILED
            d.status_message = unicode(e)
            d.active = False
            logging.debug(u'Download failed: %s' % d.status_message)

    def commit_store(self, result):
        self.store.commit()

    def stop_download(self, id):
        d = self.get_download(id)
        d.active = False
        dc = self.get_download_client(id)
        dfr = None
        if dc and dc.is_stoppable():
            logging.debug(u'Stopping download %s (%s)' % (d.id, d.description))
            dfr = defer.maybeDeferred(dc.stop)
            dfr.addCallback(self.update_status, d, Status.STOPPED)
            dfr.addErrback(self.update_status, d, Status.STOPPED)
        else:
            dfr = defer.succeed(False)
        self.store.commit()
        return dfr

    def pause(self):
        if not self.paused:
            logging.debug(u'Pausing all downloads')
            self.paused = True
            dl = [self.pause_download(d.id) for d in self.get_downloads() if d.active]
            self.store.commit()
            return defer.DeferredList(dl, consumeErrors=True)
        return defer.DeferredList([defer.succeed(False)])

    def update_status(self, result, d, status, message=None):
        if status == Status.STOPPED and d.progress == 100:
            status = Status.COMPLETED
        d.status = status
        d.status_message = message
        self.store.commit()

    def resume(self):
        if self.paused:
            logging.debug(u'Resuming all downloads')
            self.paused = False
            dl = [self.resume_download(d.id) \
                for d in self.get_downloads() if d.active]
            self.auto_queue()
            return defer.DeferredList(dl, consumeErrors=True)
        return defer.DeferredList([defer.succeed(False)])

    def add_feed(self, f):
        self.store.add(f)
        self.store.commit()
        logging.debug(u'Added new feed ' + f.url)
        return f.id

    def check_feed_success(self, parsed, feed):
        if not feed.name or not len(feed.name):
            feed.name = parsed.feed.title
        self.store.commit()
        logging.debug(u'Retrieved feed %s' % feed.name)

    def check_feed_failure(self, failure, feed):
        feed.last_error = failure.getErrorMessage()
        self.store.commit()
        logging.debug(u'Feed retrieval failed')

    def get_feeds(self):
        raise NotImplementedError('Manager must be subclassed')

    def get_feed(self, id):
        for f in self.get_feeds():
            if f.id == id:
                return f
        raise Exception('Feed not found')

    def remove_feed(self, id):
        f = self.get_feed(id)
        # Delete from database
        self.store.remove(f)
        self.store.commit()
        logging.debug(u'Removed feed %s (%s)' % (f.id, f.name))
        return True

    def get_library(self, id=None, media_type=None):
        for l in self.get_libraries():
            if id and l.id == id:
                return l
            elif media_type and l.media_type == media_type:
                return l
        return None

    def get_libraries(self):
        raise NotImplementedError('Manager must be subclassed')

    def get_option(self, name, default=None):
        return self.application.get_option(name, default);

    def get_setting(self, name, default=None):
        return self.application.get_setting(name, default);

    def get_user_directory(self):
        return os.path.expanduser(self.get_option(('downpour', 'user_directory'), '/tmp'))

class GlobalManager(Manager):

    # Start as many downloads as allowed by current configuration,
    # in the order they were added
    def auto_queue(self):
        if not self.application.is_paused():
            logging.debug(u'Running auto-queue')
            status = self.get_status()

            active = status['active_downloads']
            ulrate = status['uploadrate']
            dlrate = status['downloadrate']
            conn = status['connections']

            max_active = int(self.get_setting('max_active', 0))
            max_ulrate = int(self.get_setting('upload_rate', 0)) * 1024
            max_dlrate = int(self.get_setting('download_rate', 0)) * 1024
            max_conn = int(self.get_setting('connection_limit', 0))

            downloads = self.get_downloads()[:]

            # TODO make this fairly distributed among users
            for d in filter(lambda x: x.status == Status.QUEUED and not x.active, downloads):
                if not max_active or active < max_active:
                    self.start_download(d.id)
                    active = active + 1

            self.store.commit()

            # Auto stop downloads if we're over config limits
            if max_active and active > max_active:
                downloads.reverse()
                for d in filter(lambda x: x.active, downloads):
                    if active > max_active:
                        self.stop_download(d.id)
                        active = active - 1;
                    else:
                        break

            # Reset transfer limits
            if max_ulrate > 0:
                client_ulrate = int(max_ulrate / active)
                for d in filter(lambda x: x.active, downloads):
                    dc = self.get_download_client(d.id)
                    dc.set_upload_rate(client_ulrate)
            if max_dlrate > 0:
                client_dlrate = int(max_dlrate / active)
                for d in filter(lambda x: x.active, downloads):
                    dc = self.get_download_client(d.id)
                    dc.set_download_rate(client_dlrate)
            if max_conn > 0:
                client_conn = int(max_conn / active)
                for d in filter(lambda x: x.active, downloads):
                    dc = self.get_download_client(d.id)
                    dc.set_max_connections(client_conn)

    def get_downloads(self):
        return list(self.store.find(models.Download,
            models.Download.deleted == False).order_by(models.Download.added))

    def get_feeds(self):
        return list(self.store.find(models.Feed).order_by(models.Feed.name))

class UserManager(Manager):

    def __init__(self, application, user):
        Manager.__init__(self, application)
        self.user = user

    def add_download(self, d):
        d.user = self.user
        Manager.add_download(self, d)

    def get_downloads(self):
        if self.user.admin:
            return list(self.store.find(models.Download,
                models.Download.deleted == False
                ).order_by(models.Download.added))
        else:
            return list(self.store.find(models.Download,
                models.Download.deleted == False,
                models.Download.user_id == self.user.id
                ).order_by(models.Download.added))

    def get_feeds(self):
        if self.user.admin:
            return list(self.store.find(models.Feed
                ).order_by(models.Feed.name))
        else:
            return list(self.store.find(models.Feed,
                models.Feed.user_id == self.user.id
                ).order_by(models.Feed.name))

    def get_libraries(self):
        if self.user.admin:
            return list(self.store.find(models.Library
                ).order_by(models.Library.media_type))
        else:
            return list(self.store.find(models.Library,
                models.Library.user_id == self.user.id
                ).order_by(models.Library.media_type))

    def get_library_directory(self):
        userdir = self.user.directory
        if not userdir:
            userdir = '%s/%s' % (self.get_user_directory(), self.user.username)
        userdir = os.path.expanduser(userdir)
        if not os.path.exists(userdir):
            os.mkdir(userdir)
        return userdir

    def get_full_path(self, path, media_type=None):
        parts = [self.get_library_directory()]
        if media_type:
            libraries = self.get_libraries()
            for l in libraries:
                if l.media_type == media_type:
                    parts.append(l.directory)
                    break
        parts.append(path)
        return os.path.expanduser('/'.join(parts))
