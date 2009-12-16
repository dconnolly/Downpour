from downpour.core import models, VERSION
from storm.locals import *

def initialize_db(store):

    store.execute("CREATE TABLE state (" +
        "id INTEGER PRIMARY KEY," +
        "name TEXT," +
        "value TEXT" +
        ")")

    store.execute("CREATE TABLE settings (" +
        "id INTEGER PRIMARY KEY," +
        "name TEXT," +
        "value TEXT" +
        ")")

    store.execute("CREATE TABLE users (" +
        "id INTEGER PRIMARY KEY," +
        "username TEXT," +
        "password TEXT," +
        "email TEXT," +
        "directory TEXT," +
        "max_downloads INTEGER," +
        "max_rate INTEGER," +
        "admin BOOLEAN" +
        ")")

    store.execute("CREATE TABLE options (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "name TEXT," +
        "value TEXT," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("CREATE TABLE libraries (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "media_type TEXT," +
        "directory TEXT," +
        "pattern TEXT," +
        "keepall BOOLEAN," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("CREATE TABLE feeds (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "name TEXT," +
        "url TEXT," +
        "media_type TEXT," +
        "etag TEXT," +
        "modified INTEGER," +
        "active BOOLEAN," +
        "auto_clean BOOLEAN," +
        "last_update INTEGER," +
        "last_error TEXT," +
        "update_frequency INTEGER," +
        "queue_size INTEGER," +
        "save_priority INTEGER," +
        "download_directory TEXT," +
        "rename_pattern TEXT," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("CREATE TABLE downloads (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "feed_id INTEGER," +
        "url TEXT," +
        "filename TEXT," +
        "media_type TEXT," +
        "mime_type TEXT," +
        "description TEXT," +
        "metadata BLOB," +
        "info_hash BLOB," +
        "resume_data BLOB," +
        "active BOOLEAN," +
        "status INTEGER," +
        "status_message TEXT," +
        "progress REAL," +
        "size REAL," +
        "downloaded REAL," +
        "uploaded REAL," +
        "added INTEGER," +
        "started INTEGER," +
        "completed INTEGER," +
        "deleted BOOLEAN," +
        "imported BOOLEAN," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,"
        "FOREIGN KEY(feed_id) REFERENCES feeds(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("CREATE TABLE feed_items (" +
        "id INTEGER PRIMARY KEY," +
        "feed_id INTEGER," +
        "download_id INTEGER," +
        "guid TEXT," +
        "title TEXT," +
        "link TEXT," +
        "updated INTEGER," +
        "content TEXT," +
        "removed BOOLEAN," +
        "FOREIGN KEY(feed_id) REFERENCES feeds(id) ON DELETE CASCADE ON UPDATE CASCADE,"
        "FOREIGN KEY(download_id) REFERENCES downloads(id) ON DELETE SET NULL ON UPDATE CASCADE"
        ")")

    store.execute("CREATE TABLE files (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "directory TEXT," +
        "filename TEXT," +
        "size INTEGER," +
        "media_type TEXT," +
        "mime_type TEXT," +
        "download_id INTEGER," +
        "original_filename TEXT," +
        "description TEXT," +
        "added INTEGER," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,"
        "FOREIGN KEY(download_id) REFERENCES downloads(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("INSERT INTO state(name, value) VALUES ('schema_version', '%s')" % VERSION)
    store.execute("INSERT INTO state(name, value) VALUES ('paused', '0')")

    # Initial admin user
    store.execute("INSERT INTO users(username, password, admin) VALUES ('admin', 'password', 1)")
    store.execute("INSERT INTO users(username, password, admin) VALUES ('user', 'password', 0)")

    store.commit()
