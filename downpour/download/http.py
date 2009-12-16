from downpour.core import VERSION
from downpour.download import *
from twisted.web import http
from twisted.web.client import HTTPDownloader, _makeGetterFactory
from twisted.internet import defer
from twisted.protocols.htb import ShapedProtocolFactory
import time, os, logging

class HTTPDownloadClient(DownloadClient):

    def start(self):
        self.original_mimetype = self.download.mime_type
        self.download.status = Status.STARTING
        factoryFactory = lambda url, *a, **kw: HTTPManagedDownloader(str(self.download.url),
                                    os.path.join(self.directory, self.download.filename),
                                    statusCallback=DownloadStatus(self.download),
                                    *a, **kw)
        self.factory = _makeGetterFactory(str(self.download.url), factoryFactory)
        self.factory.deferred.addCallback(self.check_mimetype);
        self.factory.deferred.addErrback(self.errback);
        return True

    def check_mimetype(self, *args):
        self.callback(self.download.mime_type != self.original_mimetype)

    def stop(self):
        self.download.status = Status.STOPPED
        if self.factory:
            self.factory.stopFactory()
            return True
        return False

    def set_download_rate(self, rate):
        self.download_rate = rate
        self.factory.setRateLimit(rate)

class DownloadStatus(object):
    
    def __init__(self, download):
        self.download = download
        self.bytes_start = 0
        self.bytes_downloaded = 0
        self.start_time = 0

    def onConnect(self, downloader):
        self.download.status = Status.STARTING

    def onError(self, downloader):
        self.download.status = Status.FAILED
        self.download.health = 0

    def onStop(self, downloader):
        if self.download.status != Status.FAILED:
            if self.download.progress == 100:
                self.download.status = Status.COMPLETED
            else:
                self.download.status = Status.STOPPED
        self.download.elapsed =  self.download.elapsed + (time.time() - self.start_time)

    def onHeaders(self, downloader, headers):
        contentLength = 0
        if downloader.requestedPartial:
            contentRange = headers.get('content-range', None)
            start, end, contentLength = http.parseContentRange(contentRange[0])
            bytes_start = start - 1
            self.bytes_downloaded = bytes_start
        else:
            contentLength = headers.get('content-length', [0])
        self.download.size = float(contentLength[0])
        contentType = headers.get('content-type', None)
        if contentType:
            self.download.mime_type = unicode(contentType[0])
        contentDisposition = headers.get('content-disposition', None)
        if contentDisposition and contentDisposition[0].startswith('attachment'):
            newName = contentDisposition[0].split('=')[1]
            if downloader.renameFile(newName):
                self.download.filename = newName

    def onStart(self, downloader, partialContent):
        self.start_time = time.time()
        self.download.status = Status.RUNNING
        self.download.health = 100

    def onPart(self, downloader, data):
        self.bytes_downloaded = self.bytes_downloaded + len(data)
        self.download.progress = (self.bytes_downloaded / self.download.size) * 100
        self.download_rate = (self.bytes_downloaded - self.bytes_start) / (time.time() - self.start_time)
        self.download.downloadrate = self.download_rate
        self.download.downloaded = self.bytes_downloaded
        self.timeleft = (self.download.size - self.bytes_downloaded) / self.download_rate

    def onEnd(self, downloader):
        self.download.progress = 100
        self.download.status = Status.COMPLETED
        self.download_rate = (self.bytes_downloaded - self.bytes_start) / (time.time() - self.start_time)

class HTTPManagedDownloader(HTTPDownloader):

    def __init__(self, url, file, statusCallback=None, *args, **kwargs):
        self.bytes_received = 0
        self.statusHandler = statusCallback

        # Wrap protocol factory to enforce rate limits
        self.bucketFilter = ThrottledBucketFilter(rateFilter)
        self.protocol = ShapedProtocolFactory(self.protocol, self.bucketFilter)

        HTTPDownloader.__init__(self, url, file, supportPartial=1,
                                agent='Downpour v%s' % VERSION,
                                *args, **kwargs)

    def setRateLimit(self, rate=None):
        self.bucketFilter.rate = rate

    def renameFile(self, newName):
        fullName = os.path.basename(self.fileName) + newName
        # Only override filename if we're not resuming a download
        if not self.requestedPartial or not os.path.exists(self.fileName):
            self.fileName = fullName
            return True
        elif os.rename(self.fileName, fullName):
            self.fileName = fullName
            return True
        return False

    def gotHeaders(self, headers):
        HTTPDownloader.gotHeaders(self, headers)
        if self.statusHandler:
            self.statusHandler.onHeaders(self, headers)

    def pageStart(self, partialContent):
        HTTPDownloader.pageStart(self, partialContent)
        if self.statusHandler:
            self.statusHandler.onStart(self, partialContent)

    def pagePart(self, data):
        HTTPDownloader.pagePart(self, data)
        if self.statusHandler:
            self.statusHandler.onPart(self, data)

    def pageEnd(self):
        if self.statusHandler:
            self.statusHandler.onEnd(self)
        HTTPDownloader.pageEnd(self)

    def startedConnecting(self, connector):
        if (self.statusHandler):
            self.statusHandler.onConnect(self)
        HTTPDownloader.startedConnecting(self, connector)

    def clientConnectionFailed(self, connector, reason):
        if (self.statusHandler):
            self.statusHandler.onError(self)
        HTTPDownloader.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        if (self.statusHandler):
            self.statusHandler.onStop(self)
        HTTPDownloader.clientConnectionLost(self, connector, reason)

def downloadFile(url, file, statusCallback=None, contextFactory=None, *args, **kwargs):
    factoryFactory = lambda url, *a, **kw: HTTPManagedDownloader(url, file, statusCallback=statusCallback, *a, **kw)
    return _makeGetterFactory(
        url,
        factoryFactory,
        contextFactory=contextFactory,
        *args, **kwargs).deferred
