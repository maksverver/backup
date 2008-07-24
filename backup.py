#!/usr/bin/env python

from os import walk, stat
from os.path import join
from stat import *
from time import time
from logging import debug, info, warning, error, critical, exception
from defs import DEFAULT_ARGS
from compression import compressors
from init import init

from md5 import new as MD5
hash_function = lambda data: MD5(data).digest()

cache, storage = init()

def no_compression(data, level = None):
    return data

def apply_rules(path):
    return DEFAULT_ARGS


class UpdateScanner:

    def store_block(self, hash, data, compress, level):

        if cache.hasBlock(hash):
            return

        # Compress block data into 'cdata'
        try:
            compressor = compressors[compress]
        except KeyError:
            raise 'Unsupported compression method: ' + compress

        if level: cdata = compressor.compress(data, level)
        else:     cdata = compressor.compress(data)
        if len(cdata) >= len(data):
            # Compressed version is larger than uncompressed; store as is
            debug('Reverting to uncompressed data')
            compressor = compressors['none']
            cdata      = compressor.compress(data)

        # Store remotely
        info( 'Storing data block with hash %s, size %d (compressed: %d)',
              hash.encode('hex'), len(data), len(cdata) )
        storage.setBlock(hash, compressor.cid, cdata)

        # Store in cache
        cache.addBlock(hash)


    def consider_file(self, path, args):

        debug('Considering file "%s" for backup', path)

        now = time()

        # Read metadata for file
        metadata = {}
        st = stat(path)
        mtime, mode = st[ST_MTIME], st[ST_MODE]
        metadata['p'] = mode&0777
        if S_ISLNK(mode): metadata['p'] |= 01000
        if mode&S_ISUID: metadata['p'] |= 02000
        if mode&S_ISGID: metadata['p'] |= 04000
        metadata['s'] = st[ST_SIZE]
        metadata['c'] = st[ST_CTIME]
        metadata['m'] = st[ST_MTIME]
        metadata['o'] = st[ST_UID]
        metadata['g'] = st[ST_GID]
        metadata['t'] = int(time())

        # Compare modification time
        entry = cache.getEntry(path)
        if entry and entry['metadata']['m'] == mtime:
            debug('Not modified; skipping')
            return

        if mtime + args['cooldown'] > now:
            debug('Still hot; skipping')
            return

        if entry and entry['metadata']['t'] + args['period'] > now:
            debug('Recently backed up; skipping.')
            return

        # Read blocks from file
        blocks = []
        f = file(path, "rb")
        try:
            while True:
                data = f.read(args['blocksize'])
                if not data:
                    break
                hash = hash_function(data)
                self.store_block(hash, data, args['compress'], args['level'])
                blocks.append(hash)
        finally:
            f.close()

        # Compare file with cached entry
        # TODO: check a relevant portion of the metadata too?
        if entry and entry['blocks'] == blocks:
            debug('Modification time updated, but contents have not changed; touching')
            cache.setEntry(path, entry['version'], metadata, blocks)
            return

        # Select new version for this file
        if entry: version = entry['version'] + 1
        else:     version = 1

        # Store updated file remotely
        storage.setEntry(path, version, metadata, blocks)

        # Update cache
        for hash in blocks:
            cache.incBlockRef(hash)
        cache.setEntry(path, version, metadata, blocks)



    def process(self, dirpath):
        def report_exception(ex):
            warning( '%s: %s', ex.filename, ex.strerror )

        try:
            for path, dirs, files in walk(dirpath, True, report_exception):
                kept = []
                for name in dirs:
                    dirpath = join(path, name)
                    args    = apply_rules(dirpath)
                    if not args['skip']:
                        kept.append(name)
                        #consider_dir(dirpath, args)
                dirs[:] = kept

                for name in files:
                    filepath = join(path, name)
                    args     = apply_rules(filepath)
                    if not args['skip']:
                        self.consider_file(filepath, args)
        except:
            raise

        cache.updateRevision(storage)


if __name__ == "__main__":
    UpdateScanner().process('/home/maks/Desktop/Backup/test')
