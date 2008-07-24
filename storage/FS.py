'''Filesystem storage module

Stores data and metadata in a filesystem directory.

The connection string should be an (absolute) path to a directory,
    eg. "/var/db/my-storage"
When the storage is first created, this directory should not yet exist.'''

from StorageBase import StorageBase
from os import listdir, unlink, rmdir, mkdir
from os.path import pathsep, join, isdir
from base64 import urlsafe_b64encode as encode_key, urlsafe_b64decode as decode_key

class StorageFS (StorageBase):
    '''The storage class

    May raise IOError or OSError.'''

    def __init__(self, path, _username, _password, create_config = None):
        self.path = path
        if not isdir(path):
            if not create_config:
                raise Exception('path does not exist, and no configuration specified')
            mkdir(path)
            self.setConfig(create_config)
            self.setRevision(0)

    def close(self):
        '''Disconnects from the repository and cleans up.

        To be implemented in subclasses.'''
        raise MissingImplementation(self.close)

    def destroy(self):
        '''Completely erases the repository and all of its contents.
           Use with caution!'''

        for key in self.list():
            self.delete(key)
        unlink(self.path)

    def list(self):
        '''Returns a listing of object keys.'''
        for name in listdir(self.path):
            yield decode_key(name)

    def store(self, key, value):
        '''Stores an object with the given key and value.'''
        file(join(self.path, encode_key(key)), 'wb').write(value)

    def retrieve(self, key):
        '''Retrieves the value of the object with the given key, or
           returns None if no such object exists.'''
        try:
            f = file(join(self.path, encode_key(key)), 'rb')
        except IOError:
            return None
        return f.read()

    def delete(self, key):
        '''Deletes the object with the given key, if it exists.'''
        try:
            unlink(join(self.path, encode_key(key)))
        except OSError, e:
            # FIXME: use a platform-dependent constant instead of 2
            if e.errno <> 2:
                raise e
        return True
