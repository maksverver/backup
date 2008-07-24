import md5, sha

def MD5(data):
    return md5.new(data).digest()

def SHA1(data):
    return sha.new(data).digest()

functions = { 'MD5': MD5, 'SHA1': SHA1 }
