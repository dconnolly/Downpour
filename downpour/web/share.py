from downpour.web import common, auth
from twisted.web import static, server
import os, shutil, urllib, cgi, json

class SharedResource(common.Resource):

    def render(self, request, *args):
        if not self.is_logged_in(request):
            request.setHeader('Status', '401 Not Authorized')
            request.write('Authentication failed')
            request.finish()
            return server.NOT_DONE_YET
        return Resource.render(self, request, *args)

    def get_user(self, request):
        if 'username' in request.args and 'password' in request.args:
            return request.application.get_user(
                unicode(request.args['username'][0]),
                unicode(request.args['password'][0]))
        return None

class Root(SharedResource):

    def __init__(self, *args, **kwargs):
        SharedResource.__init__(self, *args, **kwargs)

    def getChild(self, path, request):
        if not self.is_logged_in(request):
            return self
        manager = self.get_manager(request)
        filepath = manager.get_library_directory()
        return File(str(filepath)).getChild(path, request)

class File(static.File):

    def __init__(self, *args, **kwargs):
        static.File.__init__(self, *args, **kwargs)

    def directoryListing(self):
        lister = DirectoryIndex(self.path,
            self.listNames(),
            self.contentTypes,
            self.contentEncodings,
            self.defaultType)
        return lister

class DirectoryIndex(static.DirectoryLister, SharedResource):

    def __init__(self, *args, **kwargs):
        static.DirectoryLister.__init__(self, *args, **kwargs)
        self.path = self.path.decode('utf8')

    def render(self, request):
        directory = os.listdir(self.path)
        directory.sort()

        manager = self.get_manager(request)
        relPath = self.path[len(manager.get_library_directory()):]
        dirs, files = self.getFilesAndDirectories(directory)
        dirs.extend(files)

        request.write(json.dumps(dirs, indent=4));
        request.finish()
        return server.NOT_DONE_YET

    def getFilesAndDirectories(self, directory):
        files = []
        dirs = []
        for path in directory:
            url = urllib.quote(path.encode('utf8'), "/")
            escapedPath = cgi.escape(path)
            if os.path.isdir(os.path.join(self.path, path)):
                url = url + '/'
                dirs.append({
                    'text': escapedPath + "/",
                    'href': url,
                    'type': 'directory',
                    'size': '',
                    'encoding': ''})
            else:
                mimetype, encoding = static.getTypeAndEncoding(path, self.contentTypes,
                                                        self.contentEncodings,
                                                        self.defaultType)
                try:
                    size = os.stat(os.path.join(self.path, path)).st_size
                except OSError:
                    continue
                files.append({
                    'text': escapedPath,
                    "href": url,
                    'type': mimetype,
                    'size': size,
                    'encoding': (encoding and '%s' % encoding or '')})
        return dirs, files
