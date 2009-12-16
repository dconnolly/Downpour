from twisted.internet import reactor
from twisted.web import server
from jinja2 import Environment, PackageLoader
from downpour.core.plugins import Plugin
from downpour.web.common import requestFactory, sessionFactory
from downpour.web.site import SiteRoot
from datetime import datetime
import os, math

class WebInterfacePlugin(Plugin):

    def setup(self, config):
        # Listen for HTTP connections
        if config is not None and config.get('port', 0) is not None:
            templateLoader = PackageLoader('downpour.web', 'templates')
            self.templateFactory = Environment(loader=templateLoader)
            templateDir = os.path.dirname(templateLoader.get_source(
                    self.templateFactory, 'base.html')[1]);

            # Custom filters for templateFactory
            self.templateFactory.filters['progressbar'] = self.progressbar
            self.templateFactory.filters['healthmeter'] = self.healthmeter
            self.templateFactory.filters['intervalformat'] = self.intervalformat
            self.templateFactory.filters['timestampformat'] = self.timestampformat
            self.templateFactory.filters['workinglink'] = self.workinglink
            self.templateFactory.filters['librarylink'] = self.librarylink

            iface = '0.0.0.0'
            if 'interface' in config:
                iface = config['interface']
            root = SiteRoot(templateDir + '/media', self.application)
            site = server.Site(root)
            site.requestFactory = requestFactory(self)
            site.sessionFactory = sessionFactory(self)
            reactor.listenTCP(int(config['port']), site, interface=iface)

    def progressbar(self, percentage, width=100, style=None, label=''):
        pixwidth = ''
        dimstyle = ''
        if type(width) == str and width.endswith('%'):
            pixwidth = str(int(percentage)) + '%'
            dimstyle = ' style="width: ' + str(width) + ';"'
        else:
            pixwidth = str(int((float(percentage)/100) * width)) + 'px'
            dimstyle = ' style="width: ' + str(width) + 'px;"'
        cssclass = ''
        if style:
            cssclass = ' ' + style
        if not percentage:
            percentage = 0
        phtml = '<div class="progressmeter"' + dimstyle + '>'
        phtml = phtml + '<div class="progress' + cssclass + '" style="width: ' + \
            str(pixwidth) + ';">&nbsp;</div>'
        phtml = phtml + '<div class="label" style="width: 100%">' + \
            str(round(percentage, 1)) + '% ' + label + '</div>'
        phtml = phtml + '</div>'
        return phtml

    def healthmeter(self, percentage, height=16):
        pixheight = int(math.ceil((float(percentage)/100) * height))
        dimstyle = ' style="height: ' + str(height) + 'px;"'
        if not percentage:
            percentage = 0
        cssclass = ' green'
        if percentage < 25:
            cssclass = ' red'
        elif percentage < 50:
            cssclass = ' yellow'
        phtml = '<div class="healthmeter' + cssclass + '"' + dimstyle + '>'
        phtml = phtml + '<div class="health' + cssclass + '" style="height: ' + \
            str(pixheight) + 'px;"></div>'
        phtml = phtml + '</div>'
        return phtml

    def intervalformat(self, seconds):
        if seconds == -1:
            return 'Infinite'

        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)

        daystr = '';
        if days > 0:
            daystr = '%dd ' % days

        return '%s%d:%.2d:%.2d' % (daystr, hours, minutes, seconds)

    def workinglink(self, file, download):
        realpath = self.application.manager.get_work_directory(download) + '/' + file
        if os.access(realpath, os.R_OK):
            return '<a target="_blank" href="/work/dldir%d/%s">%s</a>' % (download.id, file, file)
        else:
            return file

    def librarylink(self, file):
        user = file.user
        manager = self.application.get_manager(user)
        userdir = manager.get_library_directory()
        relpath = file.filename
        if file.directory:
            relpath = '%s/%s' % (file.directory, file.filename)
        if userdir:
            realpath = '%s/%s' % (userdir, relpath)
            if os.access(realpath, os.R_OK):
                return '<a target="_blank" href="/browse/%s">%s</a>' % (relpath, file.filename)
        return '%s' % relpath

    def timestampformat(self, timestamp, format):
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime(format)
