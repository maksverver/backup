'''FTP storage module

Stores data and metadata in FTP directories.

The connection string should be an FTP URL of the form:
    ftp://hostname/path/to/repository/
The trailing slash is mandatory and the path to the repository may not be
empty. Note that in the url "ftp://hostname/path/" 'path' specifies a path
relative to the working directory assigned by the server upon connection,
while "ftp://hostname//path/" specifies an absolute directory.

'''
from ftplib import FTP, error_perm
from base64 import urlsafe_b64encode as encode_key, urlsafe_b64decode as decode_key
from StringIO import StringIO
from StorageBase import StorageBase

class StorageFTP (StorageBase):
    '''The storage class'''

    def __init__(self, url, user, passw, create_config = None):
        if len(url) < 8 or url[:6] <> 'ftp://' or url[-1] <> '/':
            raise 'Invalid FTP URL: "%s"' % url
        sep      = url.find('/', 6)
        hostname = url[6:sep]
        path     = url[sep + 1:-1]
        if path == '':
            raise 'Empty repository path'

        self.conn = FTP(hostname, user, passw)

        created = False
        if create_config:
            try:
                self.conn.mkd(path)
                created = True
            except:
                pass

        self.conn.cwd(path)
        if created:
            # Create new repository
            self.conn.storbinary('STOR .keep', StringIO(''))
            self.setConfig(create_config)
            self.setRevision(0)

    def close(self):
        self.conn.quit()

    def destroy():
        '''Completely erases the repository and all of its contents.
           Use with caution!'''
        for key in self.list():
            self.delFile(key)
        self.conn.delete('.keep')
        self.conn.rmd(path)

    def list(self):
        for name in self.conn.nlst('.'):
            if name and name[0] <> '.':
                yield decode_key(name)

    def store(self, key, value):
        self.conn.storbinary('STOR ' + encode_key(key), StringIO(value))

    def retrieve(self, key):
        f = StringIO()
        try:
            self.conn.retrbinary('RETR ' + encode_key(key), f.write)
            return f.getvalue()
        except error_perm, e:
            if str(e).startswith('550'):
                # File not found (or access denied :/)
                return None
            raise

    def delete(self, key):
        self.conn.delete(encode_key(key))
