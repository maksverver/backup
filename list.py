#!/usr/bin/env python

from time import ctime
from logging import debug, info, warning, error, critical, exception
from compression import cidmap
from init import init
from sys import exit

if __name__ == '__main__':

    cache, _ = init(False)

    if not cache:
        print 'Sorry, no storage cache available'
        exit(1)

    paths = list(cache.listEntries())
    paths.sort()
    for path in paths:
        print path
        for version in cache.listVersions(path):
            print "  version %d:" % version
            entry = cache.getEntry(path)
            print "    blocks:             %d" % len(entry['blocks'])
            metadata = entry['metadata']
            if 't' in metadata:
                print "    stored at:          %s" % ctime(metadata['t'])
            if 'm' in metadata:
                print "    modification time:  %s" % ctime(metadata['m'])
        print
