'''S3 storage module

Stores data and metadata in Amazon's Simple Storage Service (S3).

The connection string should be an S3 URL; i.e.:
    http://s3.amazonaws.com/bucket/path/to/repository/
The trailing slash is mandatory.

Storage:
    blocks are stored under path/d<HASH>, where HASH is URL-safe base64-encoded.
    Metadata consists of 'cid'; the compression algorithm used.

'''

from logging import debug, info, warning, error, critical, exception
from md5 import new as MD5
from hmac import new as HMAC
import sha
from time import time as now, gmtime, strftime
from urllib import quote as urlencode, unquote as urldecode
from httplib import HTTPConnection
from xml.dom.minidom import parseString
from base64 import urlsafe_b64encode as encode_key, urlsafe_b64decode as decode_key
from StorageBase import StorageBase

def date_string(time = now()):
    "Constructs an RFC 822-compliant date string"

    return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(time))


def normalize_headers(metadata):
    "Returns normalized metadata headers for S3 authentication"

    keys = metadata.keys()
    keys.sort()
    return ''.join([ 'x-amz-meta-%s:%s\n' % (k, metadata[k]) for k in keys ])


def entry_name(path, version):
    "Returns the name of an entry object in the storage"
    return 's%s,%d' % (urlencode(path), version)

class S3Error(Exception):
    "An exception raised when an S3 request fails."

    def __init__(self, status, reason, error, message):
        self.status  = status
        self.reason  = reason
        self.error   = error
        self.message = message

    def __str__(self):
        return "%d %s: %s" % (self.status, self.reason, self.message)


def raiseOnFailure(response):
    "Raises an S3Error if the response status is not 2xx."

    if response.status/100 <> 2:
        error = response.read()
        a, b = error.find('<Message>'), error.find('</Message>')
        if a >= 0 and b >= 0:
            message = error[a + len('<Message>') : b]
        else:
            message = None
        raise S3Error(response.status, response.reason, error, message)


class StorageS3 (StorageBase):
    '''The storage class'''

    def __init__(self, url, access_id, access_key, create_config = None):
        """TODO: docs

        Raises S3Error on request failure.
        """

        if len(url) < 9 or url[:7] <> 'http://':
            raise 'Invalid HTTP URL: "%s"' % url
        sep = url.find('/', 7)
        self.hostname = url[7:sep]
        self.path     = url[sep:]
        if self.path == '':
            raise 'Empty repository path'
        sep = self.path.find('/', 1)
        self.bucket = self.path[1:sep]
        self.prefix = self.path[sep + 1:]

        self.access_id  = access_id
        self.access_key = access_key

        # Create bucket (in case it didn't exist)
        raiseOnFailure(self.execute('PUT', '/' + self.bucket))

        # Check for existence of marker
        data = self.getObject('')
        if data:
            if not create_config:
                raise "Repository not found, and no configuration specified"

            # Create new repository
            info('Creating new repository at "%s"', self.path)
            self.setConfig(create_config)
            self.setRevision(0)
            self.putObject('', '-')

    def close(self):
        pass

    def destroy(self):
        for key in self.list():
            self.delete(key)
        self.delObject('')
        self.execute('DELETE', '/' + self.bucket)
        # It's ok if this fails, since that probably means the bucket was
        # not empty; TODO: check for real error condition

    def list(self):
        for name in self.listObjects('d'):
            key = decode_key(name)
            if key:
                yield key

    def store(self, key, value):
        return self.putObject(encode_key(key), value)

    def retrieve(self, key):
        return self.getObject(encode_key(key))

    def delete(self, key):
        raiseOnFailure(self.execute('DELETE', self.path + encode_key(key)))


    #
    # Internal implementation follows
    #

    def getObject(self, path):
        """Retrieves the object at the given relative path.
           If the object does not exist, None is returned.

           Raises S3Error if the request fails"""
        response = self.execute('GET', self.path + path)
        if response.status == 404:
            return metadata, None
        raiseOnFailure(response)
        return response.read()

    def putObject(self, path, data, metadata = {}):
        """Stores an object at the given relative path.

           Raises S3Error if the request fails"""
        response = self.execute('PUT', self.path + path, '', data, metadata)
        raiseOnFailure(response)
        return True

    def listObjects(self, delimiter = None):
        """Lists objects in the repository. Only objects starting with 'prefix'
           and not containing 'delimiter' (except inside the prefix) are returned.

           May raise S3Error if request fails."""
        query = 'prefix=%s&' % urlencode(self.prefix)
        if delimiter:
            query += 'delimiter=%s&' % urlencode(delimiter)

        prefix_len = len(self.prefix)
        marker = ''
        done = False
        while not done:
            q = query + 'marker=' + marker
            response = self.execute('GET', '/' + self.bucket, q)
            raiseOnFailure(response)
            body = response.read()
            doc = parseString(body)
            for elem in doc.getElementsByTagName('Key'):
                marker = elem.firstChild.data
                yield marker[prefix_len:].encode('utf-8')
            done = True
            for elem in doc.getElementsByTagName('IsTruncated'):
                if elem.firstChild and elem.firstChild.data == 'true':
                    done = False

    def delObject(self, path):
        """Deletes the object with the given relative location
           Raises S3Error if the request fails."""
        raiseOnFailure(self.execute('DELETE', self.path + path))
        return True

    def execute(self, method, resource, query = '', data = '', metadata = { }):
        """Executes a S3 request.
        'method' is the HTTP request method (eg. GET, PUT, DELETE)
        'resource' is the absolute path to the resource ("/bucket/objectid")
        'query' is the query string without the '?'; optional.
        'data' is the data to be sent as the request body (eg. when PUTting a file)
        'metadata' is a set of additional key/value pairs to be stored;
            keys and values must be UTF-8 encoded strings"""
 
        date = date_string()
        if data: hash = MD5(data).digest().encode('base64').strip()
        else:    hash = ''
        request_data =  "%s\n%s\n\n%s\n%s%s" % (
            method, hash, date,
            normalize_headers(metadata), resource )

        auth = "AWS %s:%s" % ( self.access_id, \
            HMAC(self.access_key, request_data, sha).digest().encode('base64').strip() )

        info( 'S3 %s request on "%s" (%d bytes of data; %d metadata entries)',
              method, resource, len(data), len(metadata) )

        if query:
            resource += '?' + query

        conn = HTTPConnection(self.hostname)
        conn.putrequest(method, resource + '?' + query, True, True)
        conn.putheader('Date', date)
        conn.putheader('Host', self.hostname)
        conn.putheader('Authorization', auth)
        conn.putheader('Content-Length', str(len(data)))
        if data:
            conn.putheader('Content-Length', str(len(data)))
            conn.putheader('Content-Md5', hash)
        for key in metadata:
            conn.putheader('x-amz-meta-' + key, str(metadata[key]))
        conn.endheaders()
        conn.send(data)
        return conn.getresponse()
