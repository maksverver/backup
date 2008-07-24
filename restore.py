#!/usr/bin/env python

from time import ctime
from sys import argv, exit
from logging import debug, info, warning, error, critical, exception
from compression import cidmap
from init import init

from md5 import new as MD5
hash_function = lambda data: MD5(data).digest()

def restore(path, destination, version = None):
    '''Restores a file from the repository.
If `version` is None, the latest version is selected. The file is written to
`destination`, which must be in an existing directory. If `destination` is
None, the file is not written to disk, which in effect just verifies that the
file is stored correctly in the repository.'

    Raises IOError if the destination file cannot be opened or written.'''

    errors = False  # set whenever an error occurs, and returned in the end

    # Retrieve file entry from cache and storage
    cached_entry = cache.getEntry(path, version)
    if not cached_entry:
        if not version:
            error( 'Cache has no file "%s"; aborting. '
                   'Try to extract a specific version instead!', path)
            # We can not continue, as the storage needs to know the version
            return False
        else:
            errors = True
            error('Cache has no file "%s" with version %d', path, version)
    else:
        version = cached_entry['version']

    stored_entry = storage.getEntry(path, version)
    if not stored_entry:
        errors = True
        error('Storage has no file "%s" with version %d', path, version)

    # Figure out which entry to use; normally, the cached and stored entries
    # are the same, but we try to continue even if one is missing.
    # Sets 'entry', 'metadata' and 'blocks'.
    if cached_entry and stored_entry:
        entry            = cached_entry
        metadata, blocks = stored_entry
        if blocks <> entry['blocks']:
            errors = True
            error( 'Stored blocks do not match cached blocks; '
                   'continuing using cached blocks.' )
            blocks = entry['blocks']
        for k in entry['metadata']:
            if str(metadata.get(k)) <> str(entry['metadata'][k]):
                errors = True
                error( 'Stored metadata does not match cached metadata; '
                    'continuing using cached metadata.' )
                debug( 'Key: "%s"; cached: "%s"; stored: "%s"',
                       k, entry['metadata'][k], metadata.get(k) )
                metadata = entry['metadata']
                break
    elif cached_entry:
        warning('Continuing using cached data only')
        entry      = cached_entry
        metadadata = entry['metadata']
        blocks     = entry['blocks']
    elif stored_entry:
        warning('Continuing using stored data only')
        metadata, blocks = stored_entry
        entry = { 'path': path, 'version': version,
                  'metadata': metadata, 'blocks': blocks }
    else:
        # No entries available.
        return False

    info( 'Attempting to restore file "%s" version %d (%s); %d blocks',
          path, entry['version'], ctime(metadadata.get('t'), len(blocks) )

    # Open output file
    if destination:
        f = file(destination, 'wb')

    # Restore metadata
    # NOTE: this must be done before further writing, because if the metadata
    # includes restricted permissions, written blocks may be read by
    # unauthorized users otherwise.
    # TODO

    # Restore contents
    last_block_size = written = 0
    for b in xrange(len(entry['blocks'])):
        hash = entry['blocks'][b]
        info('Restoring block %d (hash: %s)', b, hash.encode('hex'))

        # Retrieve block
        block = storage.getBlock(hash)
        if not block:
            errors = True
            error( 'Block %d (hash: %s) not found in repository; skipped',
                    b, hash.encode('hex') )
            f.write(last_block_size*'\0')
            written += last_block_size
            # FIXME: truncate to filesize if this is the last block
        else:

            # Determine compressor to use
            cid, cdata = block
            if cid not in cidmap:
                errors = True
                error( 'Block %d (hash: %s) uses unknown compressor (cid: %s); '
                       'assuming no compression.',
                       b, hash.encode('hex'), cid )
                cid = '-'
            compressor = cidmap[cid]

            # Decompress block
            info( 'Decompressing with compressor %s (%s)', compressor.name, cid )
            try:
                data = compressor.decompress(cdata)
            except Exception, e:
                errors = True
                error( 'Decompressing of block %d (hash: %s) with '
                        'compressor %s (%s) failed; error: %s',
                        b, hash.encode('hex'), compressor.name, cid,
                        str(e) )
                data = cdata
            else:
                # Decompression ok; recompute hash
                data_hash = hash_function(data)
                if hash <> data_hash:
                    errors = True
                    error( 'Block %d (hash: %s) failed hash check (calculated: %s)',
                        b, hash.encode('hex'), data_hash.encode('hex') )

                # Keep size of last good block as an estimate of the size of
                # missing blocks
                last_block_size = len(data)

            # Write block to disk
            if destination:
                info('Writing to disk')
                f.write(data)
                written += len(data)

    f.close()

    # Check if filesize matches
    if 's' not in entry['metadata']:
        warning('No filesize recorded in metadata')
    else:
        if written <> entry['metadata']['s']:
            errors = True
            error( 'Cached filesize (%d bytes) does not match actual size of '
                   'file "%s" (%d bytes)', entry['metadata']['s'], path, size )

    return not errors


if __name__ == '__main__':
    if len(argv) == 3:
        _, path, destination = argv
        version = None
    elif len(argv) == 4:
        _, path, destination, version = argv
        try:
            version = int(version)
        except ValueError:
            error('Version is not an integer')
            exit(1)
        if version < 1:
            error('Version should be a positive integer')
            exit(1)
    else:
        print 'Usage: restore <path> <destination> [<version>]'
        exit(0)

    cache, storage = init()

    try:
        restore(path, destination, version)
    except IOError, e:
        error('Can not write to destination; %s', e)
        exit(1)
