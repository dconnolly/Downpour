from downpour.web import common
from downpour.core import models, organizer
from downpour import download
import libtorrent as lt
from twisted.web import server
from twisted.internet import defer

class Root(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)
        self.putChild('add', Add())
        self.putChild('cleanup', Cleanup())
        self.putChild('bulk', Bulk())

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]
        elif path.isdigit():
            return Detail(int(path))

    def render_GET(self, request):
        manager = self.get_manager(request)
        context = {'title': 'My Downloads',
                   'status': manager.get_status(),
                   'downloads': manager.get_downloads(),
                   'clientFactory': lambda id: manager.get_download_client(id, True),
                   'statuscode': download.Status,
                   'statusdesc': download.Status.descriptions
                   }
        return self.render_template('downloads/index.html', request, context)

class Add(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)
        self.putChild('url', AddURL())
        self.putChild('torrent', AddTorrent())

    def render_GET(self, request):
        return 'Not implemented'

class AddTorrent(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)

    def render_POST(self, request):
        if 'torrent' in request.args and len(request.args['torrent'][0]) > 0:
            d = models.Download()
            d.mime_type = u'application/x-bittorrent'
            d.metadata = request.args['torrent'][0]
            ti = lt.torrent_info(lt.bdecode(d.metadata))
            d.description = unicode(ti.name())
            d.size = int(ti.total_size())
            self.get_manager(request).add_download(d)
            request.redirect('/downloads');
            request.finish()
            return server.NOT_DONE_YET
        else:
            return self.render_template('errors/error.html', request, {
                'title': 'No Torrent Found',
                'message': 'Torrent was not uploaded'
                })

class AddURL(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)

    def render_POST(self, request):
        if 'url' in request.args and len(request.args['url'][0]) > 0:
            d = models.Download()
            d.url = unicode(request.args['url'][0])
            self.get_manager(request).add_download(d)
            request.redirect('/downloads');
            request.finish()
            return server.NOT_DONE_YET
        else:
            return self.render_template('errors/error.html', request, {
                'title': 'No URL Found',
                'message': 'URL was not specified'
                })

class Cleanup(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)

    def render_GET(self, request):
        manager = self.get_manager(request)
        for d in manager.get_downloads():
            if d.status == download.Status.COMPLETED and d.imported and not d.active:
                manager.remove_download(d.id)
        request.redirect('/downloads')
        request.finish()
        return server.NOT_DONE_YET

class Bulk(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)

    def render_POST(self, request):
        manager = self.get_manager(request)
        postrun = None
        def finish(result):
            if postrun:
                postrun()
            request.redirect('/downloads')
            request.finish()

        if 'id' in request.args and 'action' in request.args:
            action = request.args['action'][0]
            ids = request.args['id']
            dl = []

            if action == 'start':
                # Don't assign to dl, don't need to wait
                [manager.start_download(int(id)) for id in ids]
            elif action == 'stop':
                dl = [manager.stop_download(int(id)) for id in ids]
            elif action == 'restart':
                dl = [manager.stop_download(int(id)) for id in ids]
                def startall():
                    [manager.start_download(int(id)) for id in ids]
                postrun = startall
            elif action == 'remove':
                dl = [manager.remove_download(int(id)) for id in ids]

            if len(dl):
                dfl = defer.DeferredList(dl)
                dfl.addCallback(finish)
            else:
                finish(None)
        else:
            finish(None)
        return server.NOT_DONE_YET

class Detail(common.AuthenticatedResource):

    def __init__(self, id):
        common.AuthenticatedResource.__init__(self)
        self.id = id

    def getChild(self, path, request):
        if (path == ''):
            return self
        manager = self.get_manager(request)
        if manager:
            download = manager.get_download(self.id)
            if (path == 'start'):
                return Start(download)
            elif (path == 'restart'):
                return Restart(download)
            elif (path == 'stop'):
                return Stop(download)
            elif (path == 'update'):
                return Update(download)
            elif (path == 'delete'):
                return Delete(download)
        else:
            return self

    def render_GET(self, request):
        manager = self.get_manager(request)
        store = request.application.get_store()
        user = self.get_user(request)
        dl = store.find(models.Download, models.Download.id == self.id).one()
        libs = store.find(models.Library, models.Library.user_id == user.id)
        if dl.mime_type:
            template = 'downloads/detail_%s.html' % dl.mime_type.replace('/', '_')
        else:
            template = 'downloads/detail.html'
        downloadClient = manager.get_download_client(dl.id, True)
        context = {'title': dl.description,
                   'download': dl,
                   'libraries': organizer.get_media_libraries(libs),
                   'mediatypes': organizer.get_media_types(),
                   'client': downloadClient,
                   'statuscode': download.Status,
                   'statusdesc': download.Status.descriptions
                   }
        try:
            request.templateFactory.get_template(template)
            return self.render_template(template, request, context)
        except Exception:
            return self.render_template('downloads/detail.html', request, context)

class Start(common.AuthenticatedResource):

    def __init__(self, download):
        common.AuthenticatedResource.__init__(self)
        self.download = download

    def render_GET(self, request):
        manager = self.get_manager(request)
        manager.start_download(self.download.id)
        if 'from' in request.args and request.args['from'][0] == 'detail':
            request.redirect('/downloads/%s' % self.download.id)
        else:
            request.redirect('/downloads')
        request.finish()
        return server.NOT_DONE_YET

class Restart(common.AuthenticatedResource):

    def __init__(self, download):
        common.AuthenticatedResource.__init__(self)
        self.download = download

    def render_GET(self, request):
        manager = self.get_manager(request)
        dfr = manager.stop_download(self.download.id)
        def finish(result):
            manager.start_download(self.download.id)
            if 'from' in request.args and request.args['from'][0] == 'detail':
                request.redirect('/downloads/%s' % self.download.id)
            else:
                request.redirect('/downloads')
            request.finish()
        dfr.addCallback(finish)
        return server.NOT_DONE_YET

class Stop(common.AuthenticatedResource):

    def __init__(self, download):
        common.AuthenticatedResource.__init__(self)
        self.download = download

    def render_GET(self, request):
        manager = self.get_manager(request)
        dfr = manager.stop_download(self.download.id)
        def finish(result):
            if 'from' in request.args and request.args['from'][0] == 'detail':
                request.redirect('/downloads/%s' % self.download.id)
            else:
                request.redirect('/downloads')
            request.finish()
        dfr.addCallback(finish)
        return server.NOT_DONE_YET

class Update(common.AuthenticatedResource):

    def __init__(self, download):
        common.AuthenticatedResource.__init__(self)
        self.download = download

    def render_POST(self, request):
        manager = self.get_manager(request)
        converters = {
            'media_type': lambda v: unicode(v)
        }
        # Updated object from form
        for k in request.args:
            v = request.args[k][0]
            if hasattr(self.download, k) and k in converters:
                setattr(self.download, k, converters[k](request.args[k][0]))
        # Reprocess library import if it is already finished
        if self.download.status == download.Status.COMPLETED:
            manager.process_download(self.download,
                manager.get_download_client(self.download.id))
        manager.store.commit()
        request.redirect('/downloads')
        request.finish()
        return server.NOT_DONE_YET

class Delete(common.AuthenticatedResource):

    def __init__(self, download):
        common.AuthenticatedResource.__init__(self)
        self.download = download

    def render_GET(self, request):
        manager = self.get_manager(request)
        dfr = manager.remove_download(self.download.id)
        def finish(result):
            request.redirect('/downloads')
            request.finish()
        dfr.addCallback(finish)
        return server.NOT_DONE_YET
