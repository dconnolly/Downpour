from downpour.core import models, organizer
from twisted.internet import threads
import feedparser, logging
from time import time, mktime
from datetime import datetime
from storm import expr
import os

def check_feeds(manager):
    now = time()
    feeds = manager.store.find(models.Feed)
    toupdate = [f for f in feeds if (f.last_update is None or (f.update_frequency*60) + f.last_update < now)]
    if len(toupdate):
        update_feeds(toupdate, manager.application)

def update_feeds(feeds, application):
    if len(feeds):
        f = feeds.pop(0)
        modified = 0
        if not f.modified is None:
            modified = datetime.fromtimestamp(f.modified)
        d = threads.deferToThread(feedparser.parse, f.url, etag=f.etag,
                modified=modified)
        manager = application.get_manager(f.user)
        d.addCallback(feed_parsed, feeds, manager, f)
        d.addErrback(feed_parse_failed, feeds, manager, f)

def feed_parsed(parsed, feeds, manager, feed):

    logging.debug('Updating feed "%s" (%s)' % (feed.name, feed.url))

    # Update etag/lastmod for future requests
    feed.last_update = time()
    feed.last_error = None
    if 'modified' in parsed:
        feed.modified = mktime(parsed.modified.timetuple())
    if 'etag' in parsed:
        feed.etag = unicode(parsed.etag)
    manager.store.commit()

    # Check entries for new downloads
    items = parsed.entries
    if feed.save_priority == '1':
        items.reverse()

    item_count = 0
    seen_items = []

    # Prime previously-seen item map to avoid duplicate downloads
    pastitems = manager.store.find(models.FeedItem,
        models.FeedItem.feed_id == feed.id)
    for pi in pastitems:
        md = organizer.get_metadata(os.path.basename(pi.link), feed)
        seen_items.append({'d': md['d'], 'e': md['e'], 's': md['s']})

    for e in items:
        do_update = False
        updated = mktime(e.updated_parsed)

        item = manager.store.find(models.FeedItem,
            models.FeedItem.feed_id == feed.id,
            models.FeedItem.guid == e.id).one()

        # Check for enclosures
        link = e.link
        if 'enclosures' in e and len(e.enclosures):
            link = e.enclosures[0].href

        # New item
        if not item:
            do_update = True
            item = models.FeedItem()
            item.feed_id = feed.id
            item.guid = e.id
            manager.store.add(item)

        if do_update or item.updated != updated:
            # Updated with new download link, re-add
            if item.link != e.link:
                do_update = True
            item.updated = updated
            item.title = e.title
            item.link = link
            if 'content' in e:
                item.content = e.content[0].value

        if not feed.active:
            do_update = False

        if do_update:
            # Check existing library for matching episode
            filename = os.path.basename(item.link)
            metadata = organizer.get_metadata(filename, feed)
            if seen(metadata, seen_items):
                # Prevent downloading duplicate items
                do_update = False
            else:
                seen_items.append({'d': metadata['d'],
                                   'e': metadata['e'],
                                   's': metadata['s']})
                pattern = feed.rename_pattern
                if not pattern:
                    lib = manager.get_library(media_type=feed.media_type)
                    if lib:
                        pattern = lib.pattern
                if not pattern:
                    pattern = '%p'
                destfile = organizer.pattern_replace(pattern, metadata)
                if os.access(destfile, os.R_OK):
                    do_update = False
                elif metadata['z'] and (metadata['e'] or metadata['d']):
                    destdir = manager.get_full_path(os.path.dirname(destfile),
                        feed.media_type)
                    if os.access(destdir, os.R_OK):
                        for e in os.listdir(destdir):
                            emd = organizer.get_metadata('%s/%s' % (destdir, e), feed)
                            if metadata['z'] == emd['z']:
                                # Match season/episode
                                if metadata['e'] and \
                                        metadata['e'] == emd['e'] and \
                                        metadata['s'] == emd['s']:
                                    do_update = False
                                    break
                                # Match date
                                elif metadata['d'] and \
                                        metadata['d'] == emd['d']:
                                    do_update = False
                                    break

        if do_update:
            d = models.Download()
            d.feed_id = feed.id
            d.user_id = feed.user_id
            d.url = item.link
            d.description = item.title
            d.media_type = feed.media_type
            item.download = d
            manager.add_download(d)

        item_count += 1
        if feed.queue_size > 0 and item_count >= feed.queue_size:
            break;

    # Remove old downloads
    if feed.queue_size > 0:
        items = manager.store.find(models.FeedItem,
            models.FeedItem.feed_id == feed.id,
            models.FeedItem.removed == False
            ).order_by(expr.Desc(models.FeedItem.updated))
        if len(items) > feed.queue_size:
            items = items[feed.queue_size:]
            for i in items:
                logging.debug('Removing old feed item %d (%s)' % (i.id, i.title))
                if i.download:
                    for f in i.download.files:
                        realpath = '/'.join(
                            (manager.get_library_directory(feed.user),
                                file.directory, file.filename))
                        if organizer.remove_file(realpath, True):
                            i.download.files.remove(f)
                i.removed = True

    manager.store.commit()

    # Process the next feed
    if len(feeds):
        update_feeds(feeds, manager.application)

def seen(m, items):
    for i in items:
        if m['e']:
            if m['e'] == i['e'] and m['s'] == i['s']:
                return True
        elif m['d']:
            if m['d'] == i['d']:
                return True
    return False

def feed_parse_failed(failure, feeds, manager, feed):
    feed.last_update = time()
    feed.last_error = unicode(failure.getErrorMessage())
    manager.store.commit()

    if len(feeds):
        update_feeds(feeds, manager.application)
