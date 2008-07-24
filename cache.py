from os import unlink
from random import randint
from anydbm import open as dbopen
from pickle import dumps, loads
from time import time

def uuid():
    # Random 9-digit number
    return `randint(0, 10**9 - 1)`


class Cache:

    def __init__(self, dbpath, storage = None):
        if not storage:
            # Open existing cache database
            self.db = dbopen(dbpath, 'w', 0600)
        else:
            # Create new cache for existing storage
            self.db = dbopen(dbpath, 'n', 0600)
            try:
                for block in storage.listBlocks():
                    self.addBlock(block)
                for path, version in storage.listEntries():
                    metadata, blocks = storage.getEntry(path, version)
                    self.setEntry(path, version, metadata, blocks)
                    for block in blocks:
                        # TODO: report error if block does not exist 
                        self.incBlockRef(block)
                self.updateRevision(storage)
            except:
                unlink(dbpath)
                raise

    def getRevision(self):
        return int(self.db['rev'])

    def updateRevision(self, storage = None):
        rev = uuid()
        if storage:
            storage.setRevision(rev)
        self.db['rev'] = rev

    def getEntry(self, path, version = None):
        try:
            if not version:
                version = self.listVersions(path)[-1]
            metadata, blocks = loads(self.db['v%s,%d' % (path, version)])
            return { 'path': path, 'version': version,
                     'metadata': metadata, 'blocks': blocks }
        except KeyError:
            return None

    def setEntry(self, path, version, metadata, blocks):
        self.db['v%s,%d' % (path, version)] = dumps((metadata, blocks))
        key = 'i' + path
        try: versions = loads(self.db[key])
        except KeyError: versions = []
        if version not in versions:
            versions.append(version)
            self.db[key] = dumps(versions)

    def hasBlock(self, hash):
        return self.db.has_key('b' + hash)

    def addBlock(self, hash):
        self.db['b' + hash] = str(0)

    def incBlockRef(self, hash):
        key = 'b' + hash
        count = int(self.db[key])
        self.db[key] = str(count + 1)

    def decBlockRef(self, hash):
        key = 'b' + hash
        count = int(self.db[key])
        if count == 0:
            raise "reference count is zero"
        self.db[key] = str(count - 1)

    def listEntries(self):
        for key in self.db:
            if key <> '' and key[0] == 'i':
                yield key[1:]

    def listVersions(self, path):
        return loads(self.db['i' + path])
