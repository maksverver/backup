from os import getenv
from os.path import join
from logging import debug, info, warning, error, critical, exception
from ConfigParser import ConfigParser
import logging
from defs import CONFIG_DEFAULTS
from cache import Cache
import storage as storage_module

home = getenv('HOME')

def openConfig():
    paths = [ '/usr/local/etc/backup/config', '/etc/backup/config' ]
    # Add config file in home dir
    if home:
        paths = [ join(home, '.backup', 'config') ] + paths

    for path in paths:
        try:
            return file(path)
        except IOError:
            pass


def get_with_default(self, section, option, default = None):
    if ConfigParser.has_option(self, section, option):
        return ConfigParser.get(self, section, option)
    else:
        return default

def init(online = True):

    # Read config file
    f = openConfig()
    if not f:
        critical("Unable to locate the configuration file")
        return None, None
    cp = ConfigParser()
    cp.__class__.xget = get_with_default
    cp.readfp(f)

    # Initialize logging
    try: log_level = int(cp.xget('logging', 'level', logging.WARNING))
    except ValueError: log_level = logging.DEBUG
    log_path = cp.xget('logging', 'path')
    logging.basicConfig(
        format = '[%(asctime)s] %(message)s',
        level = log_level, filename = log_path )
    info('Log level %d' % log_level)
    if log_path:
        info('Logging to file "%s"' % log_path)
    else:
        info('Logging to standard output')

    # Read credentials file, if necessary
    credentials_path = cp.xget('storage', 'credentials')
    if credentials_path:
        try:
            cp.readfp(file(credentials_path))
        except IOError:
            critical("Unable to read credentials file")
            return None, None

    if not online:
        storage        = None
    else:

        # Open storage
        storage_name = cp.xget('storage', 'module')
        if not storage_name:
            critical("No storage module specified")
            return None, None

        if storage_name not in storage_module.backends:
            critical('Requested storage module "%s" not supported', storage_name)
            return None, None

        storage_class  = storage_module.backends[storage_name]
        storage = storage_class( cp.xget('storage', 'connection'), \
                                 cp.xget('storage', 'username'), \
                                 cp.xget('storage', 'password'), \
                                 CONFIG_DEFAULTS  )
        storage_config = storage.getConfig()
        if not storage_config:
            critical('No configuration stored in repository (invalid connection?)')
            return None, None

        # Merge storage config defaults
        for key in CONFIG_DEFAULTS:
            if key not in storage_config:
                storage_config[key] = CONFIG_DEFAULTS[key]

        # Check for values
        if storage_config['version'] <> '1':
            raise "Invalid storage version: %s (expected: 1)" % storage_config['version']

    # Get cache location
    if home: cache_path = join(home, '.backup', 'cache.db')
    else:    cache_path = 'cache.db'
    cache_path = cp.xget('cache', 'path', cache_path)

    try:
        cache = Cache(cache_path)
    except:
        cache = None
        warning('Could not open cache file "%s"', cache_path)
        if not online:
            info('Local cache not available; will attempt to reconstruct from remote storage')
            # Retry with online repository
            return init(True)

    if online:
        # Check cache and storage consistency
        if cache and storage.getRevision() <> cache.getRevision():
            warning("Revision mismatch between cache and storage!")
            cache = None
        if not cache:
            info("Recreating cache from remote storage...")
            cache = Cache(cache_path, storage)

    return cache, storage
