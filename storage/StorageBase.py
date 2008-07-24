from cPickle import loads, dumps as real_dumps, UnpicklingError
dumps = lambda s: real_dumps(s, 2)

# TODO: add errors to be raised from storage constructor

class StorageError (Exception):
    '''An error occured in the storage back-end.'''
    pass


class DataError (Exception):
    '''The storage had an unexpected inconsistency in the stored data.
       The data repository may be corrupt; it's probably a good idea to
       recreate it.'''

    def __init__(self, message):
        self.message = message

    def __str(self):
        return 'Data inconsistency: %s' % self.message


class MissingImplementation (Exception):
    def __init__(self, method):
        self.method = method

    def __str__(self):
        return 'Class "%s" does not implement method "%s"' % (
            self.method.im_class.__name__, self.method.__name__ )


def encode_config(config):
    "Encodes a configuration dictionary into a string."
    data = ''
    for key in config:
        data += "%s\t%s\n" % (key, config[key])
    return data

def decode_config(data):
    "Decodes a configuration string into a dictionary."
    config = {}
    for line in data.split('\n'):
        sep = line.find('\t')
        if sep >= 0:
            config[line[:sep]] = line[sep + 1:]
    return config

def entry_key(path, version):
    return 'e%d,%s' % (int(version), path)


class StorageBase:
    '''Base class for storage modules

    A storage module stores data objects that consist of a key and a value,
    both of which are opaque binary strings, can efficiently retrieve objects
    given their key, and can list all object keys.
    '''

    #
    # The following methods should be implemented by concrete base classes
    #

    def __init__(self, connection, username, password, create):
        '''Connects to the repository, or raises an exception.
        If the repository does not exist, it is created if 'create' is true,
        otherwise an exception is raised.

        To be implemented in subclasses.'''
        raise MissingImplementation(self.__init__)

    def close(self):
        '''Disconnects from the repository and cleans up.

        To be implemented in subclasses.'''
        raise MissingImplementation(self.close)

    def destroy(self):
        '''Destroys the currently connected repository -- Dangerous!

        To be implemented in subclasses.'''
        raise MissingImplementation(self.destroy)

    def list(self):
        '''Returns a listing of object keys.'''
        raise MissingImplementation(self.list)

    def store(self, key, value):
        '''Stores an object with the given key and value.'''
        raise MissingImplementation(self.store)

    def retrieve(self, key):
        '''Retrieves the value of the object with the given key, or
           returns None if no such object exists.'''
        raise MissingImplementation(self.retrieve)

    def delete(self, key):
        '''Deletes the object with the given key, if it exists.'''
        raise MissingImplementation(self.retrieve)

    #
    # The following methods form the external interface. They are implemented
    # using the low level methods above, and are not normally overridden by
    # storage modules.
    #

    def getRevision(self):
        try:
            rev = int(self.retrieve('-rev'))
        except TypeError:
            raise DataError('No revision number stored')
        except ValueError:
            raise DataError('Revision number is not an integer')
        if rev < 0:
            raise DataError('Revision number is negative')
        return rev

    def setRevision(self, rev):
        self.store('-rev', str(int(rev)))


    def getConfig(self):
        data = self.retrieve('-cfg')
        if data:
            return decode_config(data)

    def setConfig(self, config):
        self.store('-cfg', encode_config(config))


    def listBlocks(self):
        for key in self.list():
            if key and key[0] == 'b':
                yield key[1:]

    def getBlock(self, id):
        data = self.retrieve('b' + id)
        if data:
            return data[0], data[1:]

    def setBlock(self, id, cid, data):
        if len(cid) <> 1:
            raise ValueError('cid should have length 1, not %d' % len(cid))
        self.store('b' + id, cid + data)

    def delBlock(self, id):
        self.delete('b' + id)


    def listEntries(self):
        for key in self.list():
            if key and key[0] == 'e':
                sep = key.find(',')
                if sep > 0:
                    try:
                        yield key[sep + 1:], int(key[1:sep])
                    except:
                        pass

    def getEntry(self, path, version):
        data = self.retrieve(entry_key(path, version))
        if data:
            return loads(data)

    def setEntry(self, path, version, metadata, blocks):
        self.store(entry_key(path, version), dumps((metadata, blocks)))

    def delEntry(self, path, version):
        self.delete(entry_key(path, version))
