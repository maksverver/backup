''' Compression module.
Registers various compression modules, and assigns them a unique 1-character
compression id.'''

import zlib, bz2, no_compression

compressors = {
    'deflate':  zlib,
    'bzip2':    bz2,
    'none':     no_compression
}

cidmap = {
    'd':        zlib,
    'b':        bz2,
    '-':        no_compression
}

# Set names and cids
for name in compressors:
    compressors[name].name = name
for cid in cidmap:
    cidmap[cid].cid = cid
