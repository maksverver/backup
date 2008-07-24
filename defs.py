'''Definitions module.'''

# Units available for use in the configuration files, and their value.
UNITS = {
    'sec':          1,
    'second':       1,
    'seconds':      1,
    'min':         60,
    'minute':      60,
    'minutes':     60,
    'hour':      3600,
    'hours':     3600,
    'day':      86400,
    'days':     86400,
    'week':    604800,
    'weeks':   604800,
    'b':            1,
    'k':         1024,
    'kb':        1024,
    'm':      1048576,
    'mb':     1048576,
    'g':   1073741824,
    'gb':  1073741824 }


# Default storage configuration -- keys and values must be strings!
# 'version' should be 1 for the current version
# 'hash_function' should be either MD5 or SHA1 for now
CONFIG_DEFAULTS = {
    'version':          '1' }


# Default arguments for file matching
DEFAULT_ARGS = {
    'skip':         0,
    'cooldown':     1*UNITS['min'],
    'period':       1*UNITS['hour'],
    'compress':     'deflate',
    'level':        0,
    'blocksize':    1*UNITS['mb'] }         # was: 64kb

